"""
Data Processing Agent - Minimal definition (7 lines of config).

Responsible for: Processing and analyzing collected data.
Only defines: agent ID, version, tools mapping, and prompt reference.
Platform handles everything else.
"""

from .base import MinimalAgent
from tools import perform_calculation, count_words, format_data_as_json


class ProcessingAgent(MinimalAgent):
    """Processes data through calculations and text analysis."""

    AGENT_ID = "processing-agent"
    AGENT_VERSION = "1.0.0"
    PROMPT_KEY = "processing-agent@v1.0.0"
    TOOLS_CONFIG = {
        "perform_calculation": perform_calculation,
        "count_words": count_words,
        "format_data_as_json": format_data_as_json,
    }
