"""
Central Tool Registry.
Manages the singleton catalogue of all available tools across the platform deployment,
enforcing RBAC preconditions and execution bounds (timeouts) before actual invocation.
"""

import asyncio
import logging
from typing import Any, Optional

from velocity.core.context import AgentContext
from velocity.exceptions import ToolNotFoundError, ToolPermissionError, ToolTimeoutError

from .metadata import ToolMetadata

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Singleton repository for all platform tools.
    Provides rigorous execution controls mapping arbitrary function calls to 
    observable, bound processes ensuring tenant sandboxing.
    """
    
    _instance: Optional["ToolRegistry"] = None

    def __new__(cls) -> "ToolRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._registry = {}
        return cls._instance

    def __init__(self) -> None:
        # Prevent re-initialization of dictionary on subsequent __new__ calls
        if not hasattr(self, "_registry"):
            self._registry: dict[str, ToolMetadata] = {}

    def register(self, func: Any) -> None:
        """
        Ingest a `@tool` decorated function into the global catalog.
        """
        metadata: ToolMetadata | None = getattr(func, "__tool_metadata__", None)
        if not metadata:
            raise ValueError(f"Function {func.__name__} must be decorated with @tool to be registered.")
            
        if metadata.name in self._registry:
            logger.warning(f"Overriding previously registered tool: {metadata.name}")
            
        self._registry[metadata.name] = metadata
        logger.debug(f"Registered tool {metadata.name} (Requires permissions: {metadata.requires_permissions})")

    def get_metadata(self, name: str) -> ToolMetadata:
        """
        Retrieve deterministic configuration data for a tool by its routing identifier.
        """
        if name not in self._registry:
            raise ToolNotFoundError(f"Tool '{name}' is not registered on this platform node.")
        return self._registry[name]

    def get_agent_schemas(self, active_permissions: list[str]) -> list[dict[str, Any]]:
        """
        Export all tool schemas that a particular agent invocation is authorized to utilize 
        based strictly on their active intersecting RBAC permissions.
        """
        allowed_schemas = []
        for metadata in self._registry.values():
            if self._satisfies_permissions(metadata.requires_permissions, active_permissions):
                allowed_schemas.append(metadata.to_llm_schema())
        return allowed_schemas

    def _satisfies_permissions(self, required: list[str], active: list[str]) -> bool:
        """Evaluate precise intersection of required and active capability strings."""
        if not required:
            return True
        # ALL required permissions must be present in the active list
        return all(req in active for req in required)

    async def execute(
        self, 
        name: str, 
        inputs: dict[str, Any], 
        ctx: AgentContext,
        agent_permissions: list[str]
    ) -> Any:
        """
        Execute a tool safely via rigorous execution bounds.
        Validates permissions, sets async timeouts, and invokes the underlying handler.
        """
        metadata = self.get_metadata(name)
        
        # 1. Platform Permission Gate
        if not self._satisfies_permissions(metadata.requires_permissions, agent_permissions):
            raise ToolPermissionError(
                f"Agent '{ctx.agent_id}' lacks permissions to execute tool '{name}'. "
                f"Required: {metadata.requires_permissions}, Active: {agent_permissions}",
                request_id=ctx.request_id,
                agent_id=ctx.agent_id
            )
            
        # 2. Schema Validation Boundary (To be formalized in ValidationEngine Phase 4)
        # We rely on upstream Gateway matching the LLM schema parameters for now
        
        # 3. Time-bounded Execution
        try:
            # We enforce time bounding tightly since runaway functions stall multi-agent async loops
            try:
                result = await asyncio.wait_for(
                    metadata.handler(**inputs), 
                    timeout=metadata.timeout_seconds
                )
                return result
                
            except getattr(asyncio.exceptions, 'TimeoutError', asyncio.TimeoutError):
                raise ToolTimeoutError(
                    f"Tool '{name}' failed to complete within its {metadata.timeout_seconds}s SLA bound.",
                    request_id=ctx.request_id,
                    agent_id=ctx.agent_id
                )
                
        except Exception as e:
            # Re-raise standard tool level exceptions unaltered;
            # fatal loop panics are trapped at the Engine scope above.
            if isinstance(e, ToolTimeoutError):
                raise
            # Uncaught tool code logic errors are passed upwards as strings usually
            raise e
