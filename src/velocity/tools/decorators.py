"""
Tool declaration decorators.
Provides the `@tool` decorator which imbues a standard python method with 
rigid metadata containing permissions, timeouts, and JSON Schema definitions 
for seamless platform interoperability.
"""

from collections.abc import Callable
from functools import wraps
from typing import Any, cast

from .metadata import ToolMetadata
from .schema_gen import generate_json_schema_from_func


def tool(
    name: str,
    description: str,
    requires_permissions: list[str] | None = None,
    owner_team: str = "platform",
    rate_limit_per_minute: int = 120,
    timeout_seconds: float = 10.0,
    retryable: bool = False,
    tags: list[str] | None = None
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to wrap a function into a Velocity platform tool.
    
    Generates deterministic JSON Schema definitions using introspected PEP-484 typing hints.
    Injects a runtime accessible `__tool_metadata__` property.
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        # Generate the inputs schema statically once at compilation/decoration time.
        auto_input_schema = generate_json_schema_from_func(func)
        
        metadata = ToolMetadata(
            name=name,
            description=description,
            handler=func,
            input_schema=auto_input_schema,
            requires_permissions=requires_permissions or [],
            owner_team=owner_team,
            rate_limit_per_minute=rate_limit_per_minute,
            timeout_seconds=timeout_seconds,
            retryable=retryable,
            tags=tags or []
        )
        
        # Attach strictly typed metadata object to the function for the central ToolRegistry
        cast(Any, func).__tool_metadata__ = metadata
        
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # We enforce asynchronous tool handlers natively 
            # to prevent main-thread IO blocking in multi-agent orchestration.
            return await func(*args, **kwargs)
            
        return wrapper

    return decorator
