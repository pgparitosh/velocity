"""
Static and dynamic model pricing configurations.
Used by the CostManager to derive accurate USD usage values for API responses instantly 
without relying on delayed vendor billing updates.
"""


# Define pricing per 1,000 tokens in USD
# Prices represent estimates and should be configurable per deployment ideally.
MODEL_PRICING: dict[str, dict[str, float]] = {
    # Anthropic
    "claude-3-5-sonnet-latest": {"input_1k": 0.003, "output_1k": 0.015},
    "claude-3-5-haiku-latest": {"input_1k": 0.00025, "output_1k": 0.00125},
    "claude-opus-latest": {"input_1k": 0.015, "output_1k": 0.075},
    
    # OpenAI
    "gpt-4o": {"input_1k": 0.005, "output_1k": 0.015},
    "gpt-4o-mini": {"input_1k": 0.00015, "output_1k": 0.0006},
    "o1-preview": {"input_1k": 0.015, "output_1k": 0.060},
    "o1-mini": {"input_1k": 0.003, "output_1k": 0.012},
    
    # Google
    "gemini-1.5-pro": {"input_1k": 0.0035, "output_1k": 0.0105},
    "gemini-1.5-flash": {"input_1k": 0.000075, "output_1k": 0.0003},
}

def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate absolute USD cost for an isolated LLM inference execution."""
    pricing = MODEL_PRICING.get(model)
    if not pricing:
        return 0.0
        
    input_cost = (input_tokens / 1000.0) * pricing["input_1k"]
    output_cost = (output_tokens / 1000.0) * pricing["output_1k"]
    
    return input_cost + output_cost
