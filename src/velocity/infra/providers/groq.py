"""
Groq API Provider.
Wraps the `groq` Python SDK to fulfill the `ILlmProvider` contract.
"""

import json
from collections.abc import AsyncIterator
from typing import Any

from groq import AsyncGroq
from openai.types.chat import ChatCompletionMessageParam

from velocity.core.llm_gateway import ILlmProvider, LlmChunk, LlmResponse
from velocity.services.cost import calculate_cost


class GroqProvider(ILlmProvider):
    """
    Adapter bridging platform-neutral semantics to the Groq REST API.

    Normalises:
    - System prompt handling (injected as first message)
    - Tool schema conversion (flat dict → OpenAI function format)
    - Stop reason mapping ('tool_calls' → 'tool_use')
    - Token-level cost attribution via local pricing table
    """

    def __init__(self, api_key: str, models: list[str]) -> None:
        self._provider_name = "groq"
        self._supported_models = models
        self.client = AsyncGroq(api_key=api_key)

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def supported_models(self) -> list[str]:
        return self._supported_models

    def _build_messages(
        self, system_prompt: str, messages: list[dict[str, Any]]
    ) -> list[ChatCompletionMessageParam]:
        """Construct a fully typed Groq message list."""
        result: list[ChatCompletionMessageParam] = []
        if system_prompt:
            # system role is a valid ChatCompletionMessageParam
            result.append({"role": "system", "content": system_prompt})
        for m in messages:
            result.append(m)  # type: ignore[arg-type]
        return result

    def _format_tools(self, platform_tools: list[dict[str, Any]]) -> list[Any] | None:
        """Convert platform-neutral tool schemas to OpenAI function-tool format."""
        if not platform_tools:
            return None
        return [
            {
                "type": "function",
                "function": {
                    "name": t.get("name"),
                    "description": t.get("description"),
                    "parameters": t.get("input_schema"),
                },
            }
            for t in platform_tools
        ]

    async def call(
        self,
        system_prompt: str,
        tools: list[dict[str, Any]],
        messages: list[dict[str, Any]],
        model: str,
        max_tokens: int,
    ) -> LlmResponse:
        """Execute a blocking (non-streaming) LLM inference call."""
        groq_messages = self._build_messages(system_prompt, messages)
        formatted_tools = self._format_tools(tools)

        if formatted_tools:
            response = await self.client.chat.completions.create(
                model=model,
                messages=groq_messages,
                max_tokens=max_tokens,
                tools=formatted_tools,
                stream=False,
            )
        else:
            response = await self.client.chat.completions.create(
                model=model,
                messages=groq_messages,
                max_tokens=max_tokens,
                stream=False,
            )

        choice = response.choices[0]
        content = choice.message.content or ""
        stop_reason = choice.finish_reason
        normalized_reason = "tool_use" if stop_reason == "tool_calls" else "end_turn"

        extracted_tools: list[dict[str, Any]] = []
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                # Only FunctionToolCall (not CustomToolCall) has .function
                if hasattr(tc, "function"):
                    extracted_tools.append(
                        {
                            "id": tc.id,
                            "name": tc.function.name,
                            "inputs": json.loads(tc.function.arguments),
                        }
                    )

        in_tokens = response.usage.prompt_tokens if response.usage else 0
        out_tokens = response.usage.completion_tokens if response.usage else 0
        cost = calculate_cost(model, in_tokens, out_tokens)

        return LlmResponse(
            content=content,
            stop_reason=normalized_reason,
            input_tokens=in_tokens,
            output_tokens=out_tokens,
            tool_calls=extracted_tools,
            cost_usd=cost,
        )

    def stream(
        self,
        system_prompt: str,
        tools: list[dict[str, Any]],
        messages: list[dict[str, Any]],
        model: str,
        max_tokens: int,
    ) -> AsyncIterator[LlmChunk]:
        """Return an async generator that streams response chunks."""
        return self._stream_generator(system_prompt, messages, model, max_tokens)

    async def _stream_generator(
        self,
        system_prompt: str,
        messages: list[dict[str, Any]],
        model: str,
        max_tokens: int,
    ) -> AsyncIterator[LlmChunk]:
        """Internal async generator for streaming. Uses create(stream=True) to get raw chunks."""
        groq_messages = self._build_messages(system_prompt, messages)

        # create(stream=True) returns AsyncStream[ChatCompletionChunk], which is directly iterable
        stream = await self.client.chat.completions.create(
            model=model,
            messages=groq_messages,
            max_tokens=max_tokens,
            stream=True,
        )

        async for chunk in stream:
            # Each chunk has .choices; delta.content is the text piece
            if chunk.choices and chunk.choices[0].delta.content:
                yield LlmChunk(content=chunk.choices[0].delta.content, is_final=False)

        yield LlmChunk(content="", is_final=True)

    async def health_check(self) -> bool:
        """Verify API key validity via a lightweight models list call."""
        try:
            await self.client.models.list()
            return True
        except Exception:
            return False
