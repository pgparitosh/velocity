"""
Anthropic API Provider underlying integration.
Wraps the `anthropic` python SDK to fulfill the `ILlmProvider` contract logically.
"""

from collections.abc import AsyncIterator
from typing import Any

from anthropic import AsyncAnthropic

from velocity.core.llm_gateway import ILlmProvider, LlmChunk, LlmResponse
from velocity.services.cost import calculate_cost


class AnthropicProvider(ILlmProvider):
    """
    Adapter bridging platform-neutral semantics to Anthropic's Claude REST API natively.
    """

    def __init__(self, api_key: str, models: list[str]):
        self._provider_name = "anthropic"
        self._supported_models = models
        self.client = AsyncAnthropic(api_key=api_key)

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def supported_models(self) -> list[str]:
        return self._supported_models

    def _format_tools(self, platform_tools: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
        if not platform_tools:
            return None
            
        formatted = []
        for t in platform_tools:
            formatted.append({
                "name": t.get("name"),
                "description": t.get("description"),
                "input_schema": t.get("input_schema")
            })
        return formatted

    async def call(
        self, 
        system_prompt: str, 
        tools: list[dict[str, Any]], 
        messages: list[dict[str, Any]], 
        model: str, 
        max_tokens: int
    ) -> LlmResponse:
        
        # Anthropic delineates system prompts entirely separately from general messages
        kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        
        if system_prompt:
            kwargs["system"] = system_prompt
            
        formatted_tools = self._format_tools(tools)
        if formatted_tools:
            kwargs["tools"] = formatted_tools

        response = await self.client.messages.create(**kwargs)  # type: ignore
        
        # Parse mixed content blocks (text + tool_use)
        text_content = ""
        extracted_tools = []
        
        for block in response.content:
            if block.type == "text":
                text_content += block.text
            elif block.type == "tool_use":
                extracted_tools.append({
                    "id": block.id,
                    "name": block.name,
                    "inputs": block.input
                })
        
        stop_reason = response.stop_reason
        normalized_reason = "tool_use" if stop_reason == "tool_use" else "end_turn"
        
        in_tokens = response.usage.input_tokens
        out_tokens = response.usage.output_tokens
        
        cost = calculate_cost(model, in_tokens, out_tokens)
        
        return LlmResponse(
            content=text_content,
            stop_reason=normalized_reason,
            input_tokens=in_tokens,
            output_tokens=out_tokens,
            tool_calls=extracted_tools,
            cost_usd=cost
        )

    async def stream(
        self, 
        system_prompt: str, 
        tools: list[dict[str, Any]], 
        messages: list[dict[str, Any]], 
        model: str, 
        max_tokens: int
    ) -> AsyncIterator[LlmChunk]:
        """Streaming adapter chunking Anthropic Text blocks lazily."""
        kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system_prompt:
             kwargs["system"] = system_prompt

        async with self.client.messages.stream(**kwargs) as stream:  # type: ignore
             async for text in stream.text_stream:
                 yield LlmChunk(content=text, is_final=False)
             yield LlmChunk(content="", is_final=True)

    async def health_check(self) -> bool:
        """
        Anthropic lacks a distinct `/models` or lightweight health endpoint like OpenAI.
        We can issue a 1 token request dynamically, but for simplicity we rely on 
        the SDK failing locally.
        """
        return True
