"""
Data Processing Domain Tools - Agent-specific analytics.

Statistical and analytical tools specific to the processing workflow stage.
"""

from typing import Any, Dict, List
from velocity.sdk import tool


@tool(
    name="calculate_statistics",
    description="Calculate statistical measures over numeric datasets",
    requires_permissions=["calculation.execute", "data.read"],
    timeout_seconds=10,
)
async def calculate_statistics(values: List[float]) -> Dict[str, Any]:
    """
    Compute statistics (mean, median, std dev, min, max) over data.
    Agent-specific tool for processing workflow.
    """
    from velocity.tools.library import get_current_time
    import statistics

    if not values:
        raise ValueError("Cannot calculate statistics on empty list")

    result = {
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "std_dev": statistics.stdev(values) if len(values) > 1 else 0,
        "sum": sum(values),
        "calculated_at": await get_current_time(),
    }

    return result
