"""
Workflow agents package - Ultra-minimal definitions.

Agents only define:
- AGENT_ID, AGENT_VERSION, PROMPT_KEY
- TOOLS_CONFIG dict mapping tool names to functions

Platform provides:
- PromptLibrary integration
- Tool execution routing
- Observability, lifecycle, security
- Memory and context management
"""

from .base import MinimalAgent
from .data_agent import DataAgent
from .processing_agent import ProcessingAgent
from .analysis_agent import AnalysisAgent

__all__ = ["MinimalAgent", "DataAgent", "ProcessingAgent", "AnalysisAgent"]
