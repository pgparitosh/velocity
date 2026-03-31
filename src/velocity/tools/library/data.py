"""
Data global tools: weather, knowledge base, and random number generation.
"""

import asyncio
import random
from typing import Any, Dict

from velocity.tools.decorators import tool

from .basic import get_current_time


async def _now() -> str:
    """Internal helper to get current timestamp."""
    return await get_current_time()


@tool(
    name="get_weather_data",
    description="Retrieve weather information for a given location",
    requires_permissions=["external.api"],
    timeout_seconds=15,
    retryable=True,
)
async def get_weather_data(location: str) -> Dict[str, Any]:
    """Simulates external API call for weather data."""
    await asyncio.sleep(0.5)

    conditions = ["sunny", "cloudy", "rainy", "snowy", "windy"]
    temperatures = list(range(-10, 40))

    return {
        "location": location,
        "temperature_celsius": random.choice(temperatures),
        "condition": random.choice(conditions),
        "humidity_percent": random.randint(30, 90),
        "wind_speed_kmh": random.randint(0, 50),
        "last_updated": await _now(),
    }


@tool(
    name="search_knowledge_base",
    description="Search the company's knowledge base for information",
    requires_permissions=["data.read"],
    timeout_seconds=8,
)
async def search_knowledge_base(query: str, max_results: int = 5) -> Dict[str, Any]:
    """Searches a mock knowledge base."""
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

    results = [
        entry
        for entry in kb_entries
        if query.lower() in entry["title"].lower() or query.lower() in entry["content"].lower()
    ][:max_results]

    return {
        "query": query,
        "results_count": len(results),
        "results": results,
        "search_timestamp": await _now(),
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
        "generated_at": await _now(),
    }
