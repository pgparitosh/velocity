"""
Showcase Agent Tools.
Comprehensive tool suite demonstrating all platform capabilities:
- Basic operations (time, calculation)
- Data retrieval with permissions
- External API calls
- System operations
- Error handling and timeouts
"""

import asyncio
import random
import json
from typing import Any, Dict, List
from velocity.sdk import tool


@tool(
    name="get_current_time",
    description="Get the current date and time in human-readable format",
    requires_permissions=["time.read"],
    timeout_seconds=5,
)
async def get_current_time() -> str:
    """Returns current timestamp."""
    import datetime

    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


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
        "timestamp": await get_current_time(),
    }


@tool(
    name="get_weather_data",
    description="Retrieve weather information for a given location",
    requires_permissions=["external.api"],
    timeout_seconds=15,
    retryable=True,
)
async def get_weather_data(location: str) -> Dict[str, Any]:
    """Simulates external API call for weather data."""
    # Simulate API delay
    await asyncio.sleep(0.5)

    # Mock weather data (in real implementation, this would call a weather API)
    conditions = ["sunny", "cloudy", "rainy", "snowy", "windy"]
    temperatures = list(range(-10, 40))

    return {
        "location": location,
        "temperature_celsius": random.choice(temperatures),
        "condition": random.choice(conditions),
        "humidity_percent": random.randint(30, 90),
        "wind_speed_kmh": random.randint(0, 50),
        "last_updated": await get_current_time(),
    }


@tool(
    name="search_knowledge_base",
    description="Search the company's knowledge base for information",
    requires_permissions=["data.read"],
    timeout_seconds=8,
)
async def search_knowledge_base(query: str, max_results: int = 5) -> Dict[str, Any]:
    """Searches a mock knowledge base."""
    # Mock knowledge base entries
    kb_entries = [
        {"title": "Company Vacation Policy", "content": "Employees get 15 days PTO per year"},
        {"title": "Remote Work Guidelines", "content": "Remote work is available for all roles"},
        {"title": "Expense Reimbursement", "content": "Expenses must be submitted within 30 days"},
        {
            "title": "IT Support Process",
            "content": "Contact helpdesk@company.com for technical issues",
        },
        {
            "title": "Performance Reviews",
            "content": "Reviews occur quarterly in March, June, September, December",
        },
    ]

    # Simple text matching (real implementation would use semantic search)
    results = [
        entry
        for entry in kb_entries
        if query.lower() in entry["title"].lower() or query.lower() in entry["content"].lower()
    ][:max_results]

    return {
        "query": query,
        "results_count": len(results),
        "results": results,
        "search_timestamp": await get_current_time(),
    }


@tool(
    name="generate_random_number",
    description="Generate a random number within specified range",
    requires_permissions=["calculation.execute"],
    timeout_seconds=2,
)
async def generate_random_number(min_value: int = 1, max_value: int = 100) -> Dict[str, Any]:
    """Generates random numbers for demonstrations."""
    if min_value >= max_value:
        raise ValueError("min_value must be less than max_value")

    result = random.randint(min_value, max_value)
    return {
        "min_value": min_value,
        "max_value": max_value,
        "result": result,
        "generated_at": await get_current_time(),
    }


@tool(
    name="system_health_check",
    description="Perform system health checks and return status",
    requires_permissions=["admin.system"],
    timeout_seconds=10,
)
async def system_health_check() -> Dict[str, Any]:
    """Checks system components (mock implementation)."""
    # Simulate checking various system components
    components = ["database", "cache", "api_gateway", "llm_service", "monitoring"]

    status_results = {}
    for component in components:
        # Simulate some components occasionally being degraded
        is_healthy = random.random() > 0.1  # 90% healthy
        status_results[component] = {
            "status": "healthy" if is_healthy else "degraded",
            "response_time_ms": random.randint(10, 200),
            "last_checked": await get_current_time(),
        }

    overall_status = (
        "healthy" if all(r["status"] == "healthy" for r in status_results.values()) else "degraded"
    )

    return {
        "overall_status": overall_status,
        "component_status": status_results,
        "check_timestamp": await get_current_time(),
    }


@tool(
    name="format_data_as_json",
    description="Format provided data as properly structured JSON",
    requires_permissions=["data.read"],
    timeout_seconds=5,
)
async def format_data_as_json(data: Dict[str, Any]) -> str:
    """Formats data as JSON string."""
    try:
        # Validate it's already valid data
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

    # Count unique words
    unique_words = len(set(word.lower().strip(".,!?") for word in words))

    return {
        "original_text": text,
        "total_words": word_count,
        "unique_words": unique_words,
        "character_count": len(text),
        "processed_at": await get_current_time(),
    }
