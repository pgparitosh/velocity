"""
Tool Registration and Execution Framework.

Provides the `@tool` decorator for converting Python functions into LLM-compliant
tools, complete with runtime schema generation, permission requirements, and execution bounds.
"""

from .decorators import tool
from .metadata import ToolMetadata
from .registry import ToolRegistry
from .schema_gen import generate_json_schema_from_func

__all__ = [
    "tool",
    "ToolMetadata",
    "ToolRegistry",
    "generate_json_schema_from_func",
]
