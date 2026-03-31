"""
System global tools: health checks and diagnostics.
"""

import random
from typing import Any, Dict

from velocity.tools.decorators import tool

from .basic import get_current_time


async def _now() -> str:
    """Internal helper to get current timestamp."""
    return await get_current_time()


@tool(
    name="system_health_check",
    description="Perform system health checks and return status",
    requires_permissions=["admin.system"],
    timeout_seconds=10,
)
async def system_health_check() -> Dict[str, Any]:
    """Checks system components (mock implementation)."""
    components = ["database", "cache", "api_gateway", "llm_service", "monitoring"]

    status_results = {}
    for component in components:
        is_healthy = random.random() > 0.1
        status_results[component] = {
            "status": "healthy" if is_healthy else "degraded",
            "response_time_ms": random.randint(10, 200),
            "last_checked": await _now(),
        }

    overall_status = (
        "healthy" if all(r["status"] == "healthy" for r in status_results.values()) else "degraded"
    )

    return {
        "overall_status": overall_status,
        "component_status": status_results,
        "check_timestamp": await _now(),
    }
