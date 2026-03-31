"""
Basic global tools: time and calculation utilities.
"""

import datetime
from typing import Any, Dict

from velocity.tools.decorators import tool


def _now() -> str:
    """Internal helper to get formatted timestamp without async overhead."""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@tool(
    name="get_current_time",
    description="Get the current date and time in human-readable format",
    requires_permissions=["time.read"],
    timeout_seconds=5,
)
async def get_current_time() -> str:
    """Returns current timestamp."""
    return _now()


@tool(
    name="perform_calculation",
    description="Perform basic mathematical calculations (add, subtract, multiply, divide)",
    requires_permissions=["calculation.execute"],
    timeout_seconds=10,
)
async def perform_calculation(operation: str, a: float, b: float) -> Dict[str, Any]:
    """Performs mathematical operations with input validation."""
    if operation not in ["add", "subtract", "multiply", "divide"]:
        raise ValueError(f"Unsupported operation: {operation}")

    if operation == "divide" and b == 0:
        raise ValueError("Division by zero")

    if operation == "add":
        result = a + b
    elif operation == "subtract":
        result = a - b
    elif operation == "multiply":
        result = a * b
    elif operation == "divide":
        result = a / b

    return {
        "operation": operation,
        "operands": [a, b],
        "result": result,
        "timestamp": _now(),
    }
