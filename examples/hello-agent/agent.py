"""
Hello Agent Implementation.
The simplest possible agent to demonstrate the platform's core abstractions.
"""

from typing import Any, List
from velocity.sdk import AgentBase, AgentContext
from .tools import get_current_time, echo_payload

class HelloAgent(AgentBase):
    """
    A minimal agent that can greet users and tell the time.
    """
    
    AGENT_ID = "hello-agent"

    def system_prompt(self) -> str:
        """The instructions for the agent."""
        return (
            "You are a friendly Hello Agent from the Velocity platform. "
            "Your goal is to greet users and help them with simple tasks like checking the time. "
            "Always be polite and concise."
        )

    def tools(self) -> List[dict]:
        """Expose available tools to the LLM."""
        return [
            get_current_time.__tool_metadata__.to_llm_schema(),
            echo_payload.__tool_metadata__.to_llm_schema()
        ]

    async def execute_tool(self, name: str, inputs: dict, ctx: AgentContext) -> Any:
        """Route tool calls from the LLM to the handler functions."""
        if name == "get_current_time":
            return await get_current_time()
        elif name == "echo_payload":
            return await echo_payload(**inputs)
            
        raise ValueError(f"Tool '{name}' not found in HelloAgent catalog.")

    async def on_final_result(self, result: str, ctx: AgentContext) -> str:
        """Optional hook to post-process the final response."""
        return f"✨ {result}"
