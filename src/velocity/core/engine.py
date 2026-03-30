"""
Core Agent Execution Engine.
Coordinates the LLM interaction loop, executes tools concurrently,
and interfaces with platform middleware components (rate limiting, audit, etc.).
"""

import asyncio
import json
import logging
import time
from typing import Any

from velocity.core.base import AgentBase
from velocity.core.context import AgentContext
from velocity.core.llm_gateway import LLMGateway
from velocity.core.stop_conditions import StopConditions, check_stop_conditions
from velocity.memory.manager import MemoryManager

logger = logging.getLogger(__name__)


class AgentEngine:
    """
    The orchestrator for Agent lifecycle execution.
    Instantiated once per application lifetime (singleton pattern across platform processes)
    and injected with platform services (e.g. LLMGateway).
    """

    def __init__(
        self,
        llm_gateway: LLMGateway,
        memory_manager: MemoryManager | None = None,
        default_model: str = "gpt-4o",
    ):
        self.llm_gateway = llm_gateway
        self.memory_manager = memory_manager
        self.default_model = default_model
        # Middleware instances (Cost, Audit, Auth) will be injected here during Phase 4.

    async def run(
        self,
        agent: AgentBase,
        payload: str,
        tenant_id: str,
        request_id: str,
        session_id: str | None = None,
        stop_conditions: StopConditions | None = None,
    ) -> str:
        """
        Executes an agent loop until completion or boundary violation.
        """
        # 1. Initialization and Pre-Flight Context creation
        ctx = AgentContext(
            request_id=request_id,
            agent_id=agent.AGENT_ID,
            tenant_id=tenant_id,
            session_id=session_id,
        )
        conditions = stop_conditions or StopConditions()

        # Phase 4 Preview: Rate limiting, Auth checks, and Input Valiadation occur here.

        try:
            # 2. Setup System Instructions & Initial Message Queue
            prompt_content = agent.system_prompt()

            # Memory Initialization
            if self.memory_manager:
                messages = await self.memory_manager.initialize_session_context(ctx, payload)

                # Semantic knowledge injection (Long-term memory)
                # We use the initial payload as the query for relevant facts
                knowledge_block = await self.memory_manager.inject_semantic_context(ctx, [payload])
                if knowledge_block:
                    prompt_content = f"{prompt_content}\n{knowledge_block}"
            else:
                messages = [{"role": "user", "content": payload}]

            # 3. Agentic Loop Execution
            response = None
            while not check_stop_conditions(ctx, conditions):
                # Pre-LLM Extension Hook
                messages = await agent.on_before_llm_call(messages, ctx)

                # LLM Invocation
                response = await self.llm_gateway.call(
                    ctx=ctx,
                    system_prompt=prompt_content,
                    tools=agent.tools(),
                    messages=messages,
                    model=self.default_model,
                    max_tokens=4096,
                )

                if response.stop_reason == "end_turn" or not response.tool_calls:
                    # Final turn logic
                    messages.append({"role": "assistant", "content": response.content})
                    break

                if response.stop_reason == "tool_use":
                    # Parallel tool execution
                    messages.append(
                        {
                            "role": "assistant",
                            "content": response.content,
                            "tool_calls": self._format_tool_calls_for_provider(response.tool_calls),
                        }
                    )

                    tool_tasks = []
                    for t_call in response.tool_calls:
                        tool_tasks.append(self._execute_single_tool(agent, t_call, ctx))

                    results = await asyncio.gather(*tool_tasks, return_exceptions=True)

                    tool_messages = []
                    for idx, res in enumerate(results):
                        t_call_id = response.tool_calls[idx].get("id", f"call_{idx}")
                        content: str = (
                            str(res)
                            if not isinstance(res, BaseException)
                            else f"Tool execution failed: {res}"
                        )

                        tool_messages.append(
                            {"role": "tool", "tool_call_id": t_call_id, "content": content}
                        )

                    messages.extend(tool_messages)

                ctx.iteration += 1

            # 4. Final Output Processing
            final_text = ""
            if response:
                final_text = response.content

            # Persist memory
            if self.memory_manager:
                await self.memory_manager.persist_session_context(ctx, messages)

            # Application Hook for specific object parsing
            processed_result = await agent.on_final_result(final_text, ctx)

            # Phase 4 Preview: Security Layer intercepts 'processed_result' to check for PII

            ctx.mark_completed()
            return processed_result

        except Exception as e:
            # Trap fatal issues, execute agent-specific recovery, bubble the crash upwards
            await agent.on_error(e, ctx)
            ctx.mark_completed()
            raise e

    def _format_tool_calls_for_provider(
        self, tool_calls: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Convert platform-neutral tool_calls to provider-specific format (e.g., OpenAI style)."""
        return [
            {
                "id": tc["id"],
                "type": "function",
                "function": {
                    "name": tc["name"],
                    "arguments": json.dumps(tc["inputs"]),
                },
            }
            for tc in tool_calls
        ]

    async def _execute_single_tool(
        self, agent: AgentBase, tool_call: dict[str, Any], ctx: AgentContext
    ) -> str:
        """Private helper to safely execute and log a single tool execution block."""
        name = tool_call.get("name", "unknown")
        inputs = tool_call.get("inputs", {})

        start_t = time.monotonic()
        try:
            raw_result = await agent.execute_tool(name, inputs, ctx)
            formatted_result = await agent.on_after_tool_call(name, raw_result, ctx)

            elapsed_ms = (time.monotonic() - start_t) * 1000.0
            ctx.record_tool_call(name, success=True, latency_ms=elapsed_ms)

            return str(formatted_result)
        except Exception as err:
            elapsed_ms = (time.monotonic() - start_t) * 1000.0
            error_msg = str(err)
            ctx.record_tool_call(
                name, success=False, latency_ms=elapsed_ms, error_message=error_msg
            )
            # We return exceptions rather than raising so asyncio.gather doesn't fail fast horizontally
            raise err
