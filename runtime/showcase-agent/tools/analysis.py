"""
Analysis Domain Tools - Agent-specific reporting.

Tools for generating comprehensive reports and summaries.
"""

from typing import Any, Dict
from velocity.sdk import tool


@tool(
    name="generate_report",
    description="Generate a comprehensive analysis report with findings and recommendations",
    requires_permissions=["data.read", "admin.system"],
    timeout_seconds=10,
)
async def generate_report(
    title: str, findings: Dict[str, Any], severity: str = "normal"
) -> Dict[str, Any]:
    """
    Create structured report from analysis results.
    Agent-specific tool for analysis workflow.
    """
    from velocity.tools.library import get_current_time

    report = {
        "title": title,
        "severity_level": severity,
        "findings": findings,
        "recommendations": _generate_recommendations(findings, severity),
        "generated_at": await get_current_time(),
        "status": "completed",
    }

    return report


def _generate_recommendations(findings: Dict[str, Any], severity: str) -> list:
    """Generate actionable recommendations based on findings."""
    recommendations = []

    if severity == "critical":
        recommendations.append("Immediate action required")
    elif severity == "high":
        recommendations.append("Action required within 24 hours")
    else:
        recommendations.append("Monitor situation")

    recommendations.append("Document all changes made")
    recommendations.append("Review findings with stakeholders")

    return recommendations
