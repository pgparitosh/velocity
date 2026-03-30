"""
Hello Agent Tools.
Sample tools to demonstrate the @tool decorator and metadata registration.
"""

from typing import Any
from velocity.sdk import tool


@tool(
    name="get_current_time",
    description="Returns the current local time in human-readable format.",
    requires_permissions=["time.read"],
)
async def get_current_time() -> str:
    """A simple tool with no inputs."""
    import datetime

    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@tool(
    name="echo_payload",
    description="Returns exactly what was provided to demonstrate input schema mapping.",
)
async def echo_payload(data: str) -> str:
    """A simple tool with a single input."""
    return f"Echo from Velocity: {data}"
