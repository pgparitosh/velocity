"""
Formatting global tools: JSON formatting and text analysis.
"""

import json
from typing import Any, Dict

from velocity.tools.decorators import tool

from .basic import get_current_time


async def _now() -> str:
    """Internal helper to get current timestamp."""
    return await get_current_time()


@tool(
    name="format_data_as_json",
    description="Format provided data as properly structured JSON",
    requires_permissions=["data.read"],
    timeout_seconds=5,
)
async def format_data_as_json(data: Dict[str, Any]) -> str:
    """Formats data as JSON string."""
    try:
        json.dumps(data)
        return json.dumps(data, indent=2)
    except (TypeError, ValueError) as e:
        raise ValueError(f"Invalid data format: {e}")


@tool(
    name="count_words",
    description="Count words in provided text",
    requires_permissions=["data.read"],
    timeout_seconds=3,
)
async def count_words(text: str) -> Dict[str, Any]:
    """Counts words in text."""
    words = text.split()
    word_count = len(words)
    unique_words = len(set(word.lower().strip(".,!?") for word in words))

    return {
        "original_text": text,
        "total_words": word_count,
        "unique_words": unique_words,
        "character_count": len(text),
        "processed_at": await _now(),
    }
