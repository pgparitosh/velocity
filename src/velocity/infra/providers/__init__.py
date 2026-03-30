"""
Vendor-specific LLM adapters bridging the external APIs to the ILlmProvider contract.
"""

from .anthropic import AnthropicProvider
from .openai import OpenAIProvider

__all__ = [
    "AnthropicProvider",
    "OpenAIProvider",
]
