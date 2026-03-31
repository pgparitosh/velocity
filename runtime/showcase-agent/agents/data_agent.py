"""
Data Collection Agent - Minimal definition (7 lines of config).

Responsible for: Collecting time, weather, and random data.
Only defines: agent ID, version, tools mapping, and prompt reference.
Platform handles everything else.
"""

from .base import MinimalAgent
from tools import get_current_time, get_weather_data, generate_random_number


class DataAgent(MinimalAgent):
    """Collects raw data from multiple sources."""

    AGENT_ID = "data-agent"
    AGENT_VERSION = "1.0.0"
    PROMPT_KEY = "data-agent@v1.0.0"
    TOOLS_CONFIG = {
        "get_current_time": get_current_time,
        "get_weather_data": get_weather_data,
        "generate_random_number": generate_random_number,
    }
