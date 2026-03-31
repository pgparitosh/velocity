"""
Analysis Agent - Minimal definition (7 lines of config).

Responsible for: System analysis and reporting.
Only defines: agent ID, version, tools mapping, and prompt reference.
Platform handles everything else.
"""

from .base import MinimalAgent
from tools import system_health_check, search_knowledge_base


class AnalysisAgent(MinimalAgent):
    """Analyzes processed data and performs system checks."""

    AGENT_ID = "analysis-agent"
    AGENT_VERSION = "1.0.0"
    PROMPT_KEY = "analysis-agent@v1.0.0"
    TOOLS_CONFIG = {
        "system_health_check": system_health_check,
        "search_knowledge_base": search_knowledge_base,
    }
