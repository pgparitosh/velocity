"""
Google AI (Gemini) Provider.
Wraps the `google-generativeai` Python SDK to fulfill the `ILlmProvider` contract.
"""

import json
from collections.abc import AsyncIterator
from typing import Any

import google.generativeai as genai

from velocity.core.llm_gateway import ILlmProvider, LlmChunk, LlmResponse
from velocity.services.cost import calculate_cost


class GoogleProvider(ILlmProvider):
    """
    Adapter bridging platform-neutral semantics to Google's Gemini REST API.
    """

    def __init__(self, api_key: str, models: list[str]) -> None:
        self._provider_name = "google"
        self._supported_models = models
        genai.configure(api_key=api_key)

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def supported_models(self) -> list[str]:
        return self._supported_models

    def _convert_messages_to_gemini(
        self, system_prompt: str, messages: list[dict[str, Any]]
    ) -> tuple[str, list[dict[str, Any]]]:
        """Convert platform messages to Gemini format."""
        history = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "user":
                history.append({"role": "user", "parts": [content]})
            elif role == "assistant":
                parts = [content]
                if "tool_calls" in msg:
                    for tc in msg["tool_calls"]:
                        parts.append({"function_call": {"name": tc["name"], "args": tc["inputs"]}})
                history.append({"role": "model", "parts": parts})
            elif role == "tool":
                # Tool results
                history.append(
                    {
                        "role": "user",
                        "parts": [
                            {
                                "function_response": {
                                    "name": msg["tool_call_id"],
                                    "response": msg["content"],
                                }
                            }
                        ],
                    }
                )
        return system_prompt, history

    def _format_tools(self, platform_tools: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
        """Convert platform tools to Gemini function declarations."""
        if not platform_tools:
            return None
        return [
            {
                "name": t.get("name"),
                "description": t.get("description"),
                "parameters": t.get("input_schema"),
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
        """Execute a blocking LLM inference call."""
        try:
            model_instance = genai.GenerativeModel(
                model_name=model,
                system_instruction=system_prompt if system_prompt else None,
                tools=self._format_tools(tools),
            )

            if messages:
                # Use all but the last message for history
                _, history = self._convert_messages_to_gemini(system_prompt, messages[:-1])
                chat = model_instance.start_chat(history=history)
                last_msg = messages[-1]
                response = await chat.send_message_async(last_msg.get("content", ""))
            else:
                # No messages, start fresh
                chat = model_instance.start_chat()
                response = await chat.send_message_async("Hello")

            content = ""
            tool_calls = []
            if response.candidates:
                for part in response.candidates[0].content.parts:
                    if part.text:
                        content += part.text
                    if part.function_call:
                        tool_calls.append(
                            {
                                "id": "",  # Gemini doesn't provide IDs like OpenAI
                                "name": part.function_call.name,
                                "inputs": dict(part.function_call.args),
                            }
                        )

            # Estimate tokens (Gemini doesn't provide exact counts, so approximate)
            in_tokens = (
                len(str(history if "history" in locals() else []).split()) * 1.3
            )  # Rough estimate
            out_tokens = len(content.split()) * 1.3
            cost = calculate_cost(model, int(in_tokens), int(out_tokens))

            stop_reason = "tool_use" if tool_calls else "end_turn"

            return LlmResponse(
                content=content,
                stop_reason=stop_reason,
                input_tokens=int(in_tokens),
                output_tokens=int(out_tokens),
                tool_calls=tool_calls,
                cost_usd=cost,
            )
        except Exception as e:
            print(f"Error in GoogleProvider.call: {type(e).__name__}: {e}")
            raise

        if messages:
            # Use all but the last message for history
            _, history = self._convert_messages_to_gemini(system_prompt, messages[:-1])
            chat = model_instance.start_chat(history=history)
            last_msg = messages[-1]
            response = await chat.send_message_async(last_msg.get("content", ""))
        else:
            # No messages, start fresh
            chat = model_instance.start_chat()
            response = await chat.send_message_async("Hello")

        content = ""
        tool_calls = []
        if response.candidates:
            for part in response.candidates[0].content.parts:
                if part.text:
                    content += part.text
                if part.function_call:
                    tool_calls.append(
                        {
                            "id": "",  # Gemini doesn't provide IDs like OpenAI
                            "name": part.function_call.name,
                            "inputs": dict(part.function_call.args),
                        }
                    )

        # Estimate tokens (Gemini doesn't provide exact counts, so approximate)
        in_tokens = (
            len(str(history if "history" in locals() else []).split()) * 1.3
        )  # Rough estimate
        out_tokens = len(content.split()) * 1.3
        cost = calculate_cost(model, int(in_tokens), int(out_tokens))

        stop_reason = "tool_use" if tool_calls else "end_turn"

        return LlmResponse(
            content=content,
            stop_reason=stop_reason,
            input_tokens=int(in_tokens),
            output_tokens=int(out_tokens),
            tool_calls=tool_calls,
            cost_usd=cost,
        )

    async def stream(
        self,
        system_prompt: str,
        tools: list[dict[str, Any]],
        messages: list[dict[str, Any]],
        model: str,
        max_tokens: int,
    ) -> AsyncIterator[LlmChunk]:
        """Streaming is not implemented for simplicity."""
        # For now, just yield the full response as one chunk
        response = await self.call(system_prompt, tools, messages, model, max_tokens)
        yield LlmChunk(content=response.content, is_final=True)

    async def health_check(self) -> bool:
        """Check if API key is valid by listing models."""
        try:
            await genai.list_models()
            return True
        except Exception:
            return False
