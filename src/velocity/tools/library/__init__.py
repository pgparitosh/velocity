"""
Global Tool Library.

All tools in this package are automatically registered with the platform
ToolRegistry on import. They are available to any agent that references
them by name via the `global_tools` declaration on AgentBase subclasses.

Import convention:
    from velocity.tools.library import get_current_time, search_knowledge_base

Or bulk import to register everything:
    from velocity.tools import library  # noqa: F401
"""

from velocity.tools.registry import ToolRegistry

from .basic import get_current_time, perform_calculation  # noqa: F401
from .data import (  # noqa: F401
    get_weather_data,
    search_knowledge_base,
    generate_random_number,
)
from .formatting import format_data_as_json, count_words  # noqa: F401
from .system import system_health_check  # noqa: F401

# Auto-register all tools with the singleton ToolRegistry at import time.
_registry = ToolRegistry()
for _tool_name, _tool_metadata in {
    "get_current_time": get_current_time.__tool_metadata__,
    "perform_calculation": perform_calculation.__tool_metadata__,
    "get_weather_data": get_weather_data.__tool_metadata__,
    "search_knowledge_base": search_knowledge_base.__tool_metadata__,
    "generate_random_number": generate_random_number.__tool_metadata__,
    "format_data_as_json": format_data_as_json.__tool_metadata__,
    "count_words": count_words.__tool_metadata__,
    "system_health_check": system_health_check.__tool_metadata__,
}.items():
    _registry._registry[_tool_name] = _tool_metadata

__all__ = [
    "get_current_time",
    "perform_calculation",
    "get_weather_data",
    "search_knowledge_base",
    "generate_random_number",
    "format_data_as_json",
    "count_words",
    "system_health_check",
]
