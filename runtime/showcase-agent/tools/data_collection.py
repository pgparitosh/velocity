"""
Data Collection Domain Tools - Agent-specific enhancements.

These tools extend common platform tools with domain-specific logic.
"""

from typing import Any, Dict
from velocity.sdk import tool


@tool(
    name="enhanced_weather_analysis",
    description="Enhanced weather analysis combining multiple data points for insights",
    requires_permissions=["external.api", "data.read"],
    timeout_seconds=15,
)
async def enhanced_weather_analysis(location: str, historical_days: int = 3) -> Dict[str, Any]:
    """
    Analyze weather patterns by combining current data with historical context.
    This is agent-specific - builds on common get_weather_data tool.
    """
    from velocity.tools.library import get_weather_data, get_current_time

    current_weather = await get_weather_data(location)

    # Simulate historical trend (in real system, would fetch from DB)
    trend = "warming" if current_weather["temperature_celsius"] > 15 else "cooling"
    confidence = 0.85

    return {
        "location": location,
        "current_weather": current_weather,
        "trend": trend,
        "trend_confidence": confidence,
        "historical_days_analyzed": historical_days,
        "analysis_timestamp": await get_current_time(),
    }
