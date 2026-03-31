"""
Velocity Agent SDK.
The single, stable import path for Agent Developers mapped across the organization.

Usage:
    from velocity.sdk import AgentBase, AgentContext, tool, ToolRegistry
"""

from velocity.core.base import AgentBase
from velocity.core.context import AgentContext
from velocity.tools.decorators import tool
from velocity.tools.registry import ToolRegistry

# Exposing core decorators and abstractions to the user package-space seamlessly
__all__ = [
    "AgentBase",
    "AgentContext",
    "tool",
    "ToolRegistry",
]
