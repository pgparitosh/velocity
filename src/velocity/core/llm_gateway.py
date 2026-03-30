"""
LLM Gateway.
Provides a centralized, provider-agnostic access point for LLM interactions.
Handles resilience via Circuit Breakers, Exponential Backoff, and cross-provider Fallbacks.
"""

import asyncio
import logging
import random
import time
from collections.abc import AsyncIterator
from typing import Any, Protocol, runtime_checkable

from velocity.core.circuit_breaker import CircuitBreaker
from velocity.core.context import AgentContext
from velocity.exceptions import LLMUnavailableError

logger = logging.getLogger(__name__)


class LlmChunk:
    """Represents a chunk of a streaming LLM response."""

    __slots__ = ("content", "is_final")

    def __init__(self, content: str, is_final: bool = False):
        self.content = content
        self.is_final = is_final


class LlmResponse:
    """Represents a complete LLM response."""

    __slots__ = (
        "content",
        "stop_reason",
        "input_tokens",
        "output_tokens",
        "tool_calls",
        "cost_usd",
    )

    def __init__(
        self,
        content: str,
        stop_reason: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        tool_calls: list[dict[str, Any]] | None = None,
        cost_usd: float = 0.0,
    ):
        self.content = content
        self.stop_reason = stop_reason
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.tool_calls = tool_calls or []
        self.cost_usd = cost_usd


@runtime_checkable
class ILlmProvider(Protocol):
    """Protocol for provider integrations (e.g., Anthropic, OpenAI)."""

    @property
    def provider_name(self) -> str: ...

    @property
    def supported_models(self) -> list[str]: ...

    async def call(
        self,
        system_prompt: str,
        tools: list[dict[str, Any]],
        messages: list[dict[str, Any]],
        model: str,
        max_tokens: int,
    ) -> LlmResponse: ...

    def stream(
        self,
        system_prompt: str,
        tools: list[dict[str, Any]],
        messages: list[dict[str, Any]],
        model: str,
        max_tokens: int,
    ) -> AsyncIterator[LlmChunk]: ...

    async def health_check(self) -> bool: ...


class LLMGateway:
    """
    Central orchestration point for LLM calls.
    Enforces rules and routes requests transparently across actual backend providers.
    Provides robust retry-with-jitter and failover mechanisms.
    """

    def __init__(
        self,
        providers: dict[str, ILlmProvider],
        default_provider: str,
        fallback_chain: list[str] | None = None,
        max_retries: int = 3,
    ) -> None:
        self.providers = providers
        self.default_provider = default_provider
        self.fallback_chain = fallback_chain or list(providers.keys())
        self.max_retries = max_retries

        # Instantiate an isolated circuit breaker for each provider domain
        self.circuit_breakers = {name: CircuitBreaker() for name in providers}

    def _get_provider(self, provider_name: str) -> ILlmProvider:
        if provider_name not in self.providers:
            # Revert to default or fail
            return self.providers[self.default_provider]
        return self.providers[provider_name]

    async def _execute_with_resilience(
        self, call_func: Any, provider_name: str, *args: Any, **kwargs: Any
    ) -> Any:
        """Helper to orchestrate calls through backoffs and failovers."""

        exceptions = []
        providers_to_try = [provider_name]

        # Add fallback chain if the initial provider isn't already the last line of defense
        for fallback in self.fallback_chain:
            if fallback not in providers_to_try and fallback in self.providers:
                providers_to_try.append(fallback)

        for current_provider_name in providers_to_try:
            breaker = self.circuit_breakers[current_provider_name]
            provider = self._get_provider(current_provider_name)

            for attempt in range(self.max_retries + 1):
                if not breaker.allow_request():
                    logger.warning(
                        f"Circuit open for provider {current_provider_name}. Failing fast."
                    )
                    break  # Break retry loop, move to next fallback provider

                try:
                    # Note: We aren't doing the actual runtime measurement here;
                    # the engine loops will handle measuring start/stop for tracing.
                    result = await call_func(provider, *args, **kwargs)
                    breaker.record_success()
                    return result

                except Exception as e:
                    breaker.record_failure()
                    exceptions.append(e)

                    if attempt == self.max_retries:
                        break  # Exhausted retries for this provider

                    # Exponential backoff with jitter (1s, 2s, 4s...)
                    sleep_time = (2**attempt) + (random.uniform(0, 0.2))
                    logger.warning(
                        f"LLM Provider '{current_provider_name}' error: {type(e).__name__}: {e}. "
                        f"Retrying in {sleep_time:.2f}s... (Attempt {attempt + 1}/{self.max_retries})"
                    )
                    await asyncio.sleep(sleep_time)

        # If we exit the loops, we exhausted all providers
        raise LLMUnavailableError(
            "All LLM providers degraded or exhausted retry limits.",
            details={"underlying_exceptions": str(exceptions)},
        )

    async def call(
        self,
        ctx: AgentContext,
        system_prompt: str,
        tools: list[dict[str, Any]],
        messages: list[dict[str, Any]],
        model: str,
        max_tokens: int,
        preferred_provider: str | None = None,
    ) -> LlmResponse:
        """
        Executes a resilience-wrapped LLM text generation sequence.
        Captures LLM calls to the provided AgentContext.
        """
        target_provider = preferred_provider or self.default_provider

        start_time = time.monotonic()

        async def _do_call(provider: ILlmProvider) -> LlmResponse:
            return await provider.call(system_prompt, tools, messages, model, max_tokens)

        response: LlmResponse = await self._execute_with_resilience(_do_call, target_provider)

        latency = (time.monotonic() - start_time) * 1000.0

        ctx.record_llm_call(
            model=model,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            call_cost_usd=response.cost_usd,
            latency_ms=latency,
        )

        return response

    async def stream(
        self,
        ctx: AgentContext,
        system_prompt: str,
        tools: list[dict[str, Any]],
        messages: list[dict[str, Any]],
        model: str,
        max_tokens: int,
        preferred_provider: str | None = None,
    ) -> AsyncIterator[LlmChunk]:
        """
        Returns a lazy async iterator over LLM response chunks.
        Note: Token usage recording during streaming requires tracking total chunks yielded.
        """
        target_provider = preferred_provider or self.default_provider
        provider = self._get_provider(target_provider)

        # Directly yield from the provider stream (no resilience wrapper for async generators)
        async for chunk in provider.stream(system_prompt, tools, messages, model, max_tokens):
            yield chunk
