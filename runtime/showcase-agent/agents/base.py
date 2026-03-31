"""
Minimal Base Agent - DRY principle for all agents.

All agents inherit from this base to eliminate boilerplate.
"""

from typing import Any, List
from velocity.sdk import AgentBase, AgentContext


class MinimalAgent(AgentBase):
    """
    Minimal agent base class following DRY principle.
    Subclasses only define: AGENT_ID, AGENT_VERSION, and tools mapping.
    """

    # Override in subclasses
    AGENT_ID: str = "base-agent"
    AGENT_VERSION: str = "1.0.0"
    TOOLS_CONFIG: dict = {}  # {"tool_name": tool_function, ...}
    PROMPT_KEY: str = "base-agent@v1.0.0"

    def system_prompt(self) -> str:
        """Platform loads actual prompt from PromptLibrary using this key."""
        return self.PROMPT_KEY

    def tools(self) -> List[dict]:
        """Export tool schemas for all configured tools."""
        schemas = []
        for tool_func in self.TOOLS_CONFIG.values():
            metadata = getattr(tool_func, "__tool_metadata__", None)
            if metadata:
                schemas.append(metadata.to_llm_schema())
        return schemas

    async def execute_tool(self, name: str, inputs: dict, ctx: AgentContext) -> Any:
        """Route tool calls with minimal logic."""
        if name not in self.TOOLS_CONFIG:
            raise ValueError(f"Unknown tool: {name}")

        tool_func = self.TOOLS_CONFIG[name]

        # Handle tools with no parameters
        if not inputs:
            return await tool_func()

        return await tool_func(**inputs)
