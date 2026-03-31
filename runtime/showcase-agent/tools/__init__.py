"""
Showcase Agent Tools - Organized by functionality domain.

Imports:
1. Common platform tools from velocity.tools.library
2. Agent-specific tools from local domain modules
"""

# Import common tools from platform library
from velocity.tools.library import (
    get_current_time,
    perform_calculation,
    get_weather_data,
    search_knowledge_base,
    generate_random_number,
    format_data_as_json,
    count_words,
    system_health_check,
)

# Import agent-specific tools (only if needed for advanced workflows)
# Most agents use common tools only; uncomment as needed:
# from .data_collection import enhanced_weather_analysis
# from .processing import calculate_statistics
# from .analysis import generate_report

__all__ = [
    # Common platform tools (used by all agents)
    "get_current_time",
    "perform_calculation",
    "get_weather_data",
    "search_knowledge_base",
    "generate_random_number",
    "format_data_as_json",
    "count_words",
    "system_health_check",
]
