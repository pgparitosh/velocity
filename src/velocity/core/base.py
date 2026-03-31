"""
AgentBase contract.
This is the foundational abstraction that every Agent in the Velocity platform must implement.
By conforming to this contract, an agent automatically inherits all cross-cutting resilience, 
observability, and compliance features.
"""

from abc import ABC, abstractmethod
from typing import Any

from velocity.core.context import AgentContext
from velocity.exceptions import ToolNotFoundError
from velocity.tools.registry import ToolRegistry


class AgentBase(ABC):
    """
    The baseline contract for building AI Agents on the Velocity platform.

    Subclasses must implement the required abstract methods for system behavior.
    Optional hooks are provided for advanced manipulation of the semantic flow.

    --- Tool Declaration ---

    Agents can use two kinds of tools:

    1. **global_tools** — tools registered in the platform's ToolRegistry.
       Declare them as a list of string names:
           global_tools = ["get_current_time", "search_knowledge_base"]
       The base class automatically resolves their schemas and routes execution
       through ToolRegistry (enforcing permissions, timeouts, etc.).

    2. **local_tools** — agent-specific tool functions not in the registry.
       Declare them as a list of decorated functions (with `@tool`):
           local_tools = [my_custom_tool]
       The base class extracts their schemas and executes them directly
       as a fallback in execute_tool.

    You can use both, either, or neither. If you override `tools()` or
    `execute_tool()` entirely, your override takes full control.

    --- Default tools() and execute_tool() Behavior ---

    If you do NOT override them, the base class provides working defaults:
    - `tools()` returns merged schemas from global_tools + local_tools
    - `execute_tool()` tries global registry first, then falls back to local_tools
    """

    # Every agent must declare a unique identifier for routing and metrics.
    AGENT_ID: str = "undefined_agent"

    # --- TOOL DECLARATION (optional override) ---

    global_tools: list[str] = []
    local_tools: list = []

    # --- REQUIRED METHODS ---

    @abstractmethod
    def system_prompt(self) -> str:
        """
        Define the core identity and persona of the agent.
        Returns the raw prompt string, or a PromptRef pointer (e.g., 'expense-agent@v2').
        """
        pass

    def tools(self) -> list[dict[str, Any]]:
        """
        Provide the list of tool schemas available to this agent during execution.

        Default implementation merges schemas from:
        - global_tools: resolved from ToolRegistry by name
        - local_tools: extracted from each tool function's __tool_metadata__

        Override if you need fully dynamic tool behaviour.
        """
        schemas: list[dict[str, Any]] = []
        registry = ToolRegistry()

        # Resolve global tool schemas
        for tool_name in self.global_tools:
            try:
                metadata = registry.get_metadata(tool_name)
                schemas.append(metadata.to_llm_schema())
            except Exception:
                # Skip unregistered global tools gracefully
                pass

        # Add local tool schemas
        for func in self.local_tools:
            metadata = getattr(func, "__tool_metadata__", None)
            if metadata:
                schemas.append(metadata.to_llm_schema())

        return schemas

    async def execute_tool(self, name: str, inputs: dict[str, Any], ctx: AgentContext) -> Any:
        """
        Execute a tool call received from the LLM.

        Default implementation:
        1. Checks global tools in ToolRegistry first
        2. Falls back to local_tools if not found globally
        3. Raises ValueError if the tool is not found

        Override if you need custom routing or execution behaviour.
        """
        registry = ToolRegistry()

        # 1. Try global tools in the registry
        try:
            metadata = registry.get_metadata(name)
            return await metadata.handler(**inputs)
        except ToolNotFoundError:
            pass  # Not in global registry — try local

        # 2. Fallback to local tools
        for func in self.local_tools:
            loc_meta = getattr(func, "__tool_metadata__", None)
            if loc_meta and loc_meta.name == name:
                return await func(**inputs)

        # 3. Not found anywhere
        raise ValueError(f"Unknown tool: {name}")

    # --- OPTIONAL EXTENSION HOOKS ---

    async def on_before_llm_call(
        self, messages: list[dict[str, Any]], ctx: AgentContext
    ) -> list[dict[str, Any]]:
        """
        Opportunity for the agent to inspect or augment the message list before it goes out.
        Most agents will not need to override this unless doing dynamic few-shot injection.
        """
        return messages

    async def on_after_tool_call(self, tool_name: str, result: Any, ctx: AgentContext) -> Any:
        """
        Opportunity to restructure a tool result before it is appended to the context.
        """
        return result

    async def on_final_result(self, result: str, ctx: AgentContext) -> str:
        """
        Post-flight hook to sanitize, translate, or finalize the agent's ultimate textual output 
        before returning control to the caller.
        """
        return result

    def parse_result(self, text: str, ctx: AgentContext) -> dict[str, Any]:
        """
        If the agent should return structured data instead of unstructured text, 
        override this method to define the parsing logic (e.g., extracting JSON blocks).
        """
        return {"output": text}

    async def on_error(self, error: Exception, ctx: AgentContext) -> None:
        """
        Custom error handling and recovery hook. 
        Executed when the platform encounters a critical error preventing progress.
        """
        return None
