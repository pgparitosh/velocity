"""
Tool abstractions and metadata formats.
Provides the rigorous dataclasses required to describe and execute Python functions 
securely within the platform's multi-tenant execution bounds.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ToolMetadata:
    """
    Holds the deterministic metadata and constraints for a platform tool.
    This serves as the configuration object carried by the `__tool_metadata__` 
    attribute injected by the `@tool` decorator.
    """
    
    name: str
    description: str
    handler: Callable[..., Any]
    
    # Validation & Routing Data
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    
    # RBAC & Identity Properties 
    requires_permissions: list[str] = field(default_factory=list)
    owner_team: str = "platform"
    
    # Resilience Constraints
    rate_limit_per_minute: int = 120
    timeout_seconds: float = 10.0
    retryable: bool = False
    
    # Observability Tags
    tags: list[str] = field(default_factory=list)

    def to_llm_schema(self) -> dict[str, Any]:
        """
        Produce a spec-compliant JSON Schema describing this tool for Anthropic/OpenAI APIs.
        """
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema
        }
