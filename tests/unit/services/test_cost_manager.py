import pytest

from velocity.services.cost.pricing import MODEL_PRICING, calculate_cost


def test_calculate_cost_known_model():
    # gpt-4o: input_1k=0.005, output_1k=0.015
    # 2000 input tokens = 0.01
    # 1000 output tokens = 0.015
    # Total = 0.025
    cost = calculate_cost("gpt-4o", 2000, 1000)
    assert pytest.approx(cost) == 0.025

def test_calculate_cost_unknown_model():
    cost = calculate_cost("non-existent-model", 1000, 1000)
    assert cost == 0.0
    
def test_calculate_cost_zero_tokens():
    cost = calculate_cost("gpt-4o", 0, 0)
    assert cost == 0.0

def test_model_pricing_coverage():
    # Ensure our common models are in the pricing dict
    assert "gpt-4o" in MODEL_PRICING
    assert "claude-3-5-sonnet-latest" in MODEL_PRICING
    assert "gemini-1.5-flash" in MODEL_PRICING
