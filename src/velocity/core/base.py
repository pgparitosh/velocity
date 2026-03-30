"""
AgentBase contract.
This is the foundational abstraction that every Agent in the Velocity platform must implement.
By conforming to this contract, an agent automatically inherits all cross-cutting resilience, 
observability, and compliance features.
"""

from abc import ABC, abstractmethod
from typing import Any

from velocity.core.context import AgentContext


class AgentBase(ABC):
    """
    The baseline contract for building AI Agents on the Velocity platform.
    
    Subclasses must implement the required abstract methods for system behavior.
    Optional hooks are provided for advanced manipulation of the semantic flow.
    """

    # Every agent must declare a unique identifier for routing and metrics.
    AGENT_ID: str = "undefined_agent"

    # --- REQUIRED METHODS ---

    @abstractmethod
    def system_prompt(self) -> str:
        """
        Define the core identity and persona of the agent.
        Returns the raw prompt string, or a PromptRef pointer (e.g., 'expense-agent@v2').
        """
        pass

    @abstractmethod
    def tools(self) -> list[dict[str, Any]]:
        """
        Provide the list of tool schemas available to this agent during execution.
        Formatted according to standard LLM tool schema specifications.
        """
        pass

    @abstractmethod
    async def execute_tool(self, name: str, inputs: dict[str, Any], ctx: AgentContext) -> Any:
        """
        Execute business logic corresponding to a tool call received from the LLM.
        
        Args:
            name: The internal tool routing identifier.
            inputs: Tool payload arguments exactly as modeled by the tool schema.
            ctx: The tracing context, in case the tool needs tenant or parent tracing ids.
            
        Returns:
            A stringifiable result indicating the outcome of the tool execution.
        """
        pass

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
