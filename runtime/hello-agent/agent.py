"""
Hello Agent Implementation.
The simplest possible agent to demonstrate the platform's core abstractions.
This agent showcases key platform features: tool execution, context management, logging, and security (PII checks via platform).
"""

import logging
from typing import Any, List
from velocity.sdk import AgentBase, AgentContext
from tools import get_current_time, echo_payload

logger = logging.getLogger(__name__)


class HelloAgent(AgentBase):
    """
    A minimal agent that greets users and tells the time.
    Demonstrates platform features: tool routing, session context, audit logging, and security.
    """

    AGENT_ID = "hello-agent"

    def system_prompt(self) -> str:
        """Platform-managed system prompt for consistent agent behavior."""
        return (
            "You are a friendly Hello Agent from the Velocity platform. "
            "Your goal is to greet users and help them with simple tasks like checking the time. "
            "Always be polite and concise. Do not use emojis in your output."
        )

    def tools(self) -> List[dict]:
        """Expose available tools to the LLM via platform's tool schema conversion."""
        return [
            get_current_time.__tool_metadata__.to_llm_schema(),
            echo_payload.__tool_metadata__.to_llm_schema(),
        ]

    async def execute_tool(self, name: str, inputs: dict, ctx: AgentContext) -> Any:
        """Route tool calls to handlers; platform handles execution logging and error tracking."""
        logger.info(f"Executing tool '{name}' with inputs: {inputs}")
        if name == "get_current_time":
            result = await get_current_time()
        elif name == "echo_payload":
            result = await echo_payload(**inputs)
        else:
            raise ValueError(f"Tool '{name}' not found in HelloAgent catalog.")

        logger.info(f"Tool '{name}' executed successfully")
        return result

    async def on_before_llm_call(self, messages: List[dict], ctx: AgentContext) -> List[dict]:
        """Platform hook for pre-LLM processing (e.g., injecting context)."""
        logger.debug("Pre-LLM call hook triggered")
        return messages

    async def on_after_tool_call(self, tool_name: str, result: Any, ctx: AgentContext) -> Any:
        """Platform hook for post-tool processing."""
        logger.debug(f"Post-tool call hook for '{tool_name}': {result}")
        return result

    async def on_final_result(self, result: str, ctx: AgentContext) -> str:
        """Platform hook for final result processing; security layer checks for PII here."""
        logger.info("Final result processed")
        return result

    async def on_error(self, error: Exception, ctx: AgentContext) -> None:
        """Platform error handling hook for recovery or logging."""
        logger.error(f"Agent error: {error}")
