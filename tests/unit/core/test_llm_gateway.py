from unittest.mock import AsyncMock, MagicMock

import pytest

from velocity.core.context import AgentContext
from velocity.core.llm_gateway import ILlmProvider, LLMGateway, LlmResponse
from velocity.exceptions import LLMUnavailableError


@pytest.fixture
def mock_provider():
    provider = MagicMock(spec=ILlmProvider)
    provider.provider_name = "mock"
    provider.supported_models = ["gpt-4o"]
    return provider

@pytest.fixture
def gateway(mock_provider):
    return LLMGateway(
        providers={"mock": mock_provider},
        default_provider="mock",
        max_retries=1
    )

@pytest.mark.asyncio
async def test_llm_gateway_successful_call(gateway, mock_provider):
    ctx = AgentContext(request_id="r1", agent_id="a1", tenant_id="t1", user_id="u1")
    mock_provider.call = AsyncMock(return_value=LlmResponse(
        content="Hello!", stop_reason="end_turn", input_tokens=10, output_tokens=5, cost_usd=0.001
    ))
    
    response = await gateway.call(ctx, "sys", [], [], "gpt-4o", 100)
    assert response.content == "Hello!"
    assert ctx.cost_usd == 0.001

@pytest.mark.asyncio
async def test_llm_gateway_retry_on_failure(gateway, mock_provider):
    ctx = AgentContext(request_id="r1", agent_id="a1", tenant_id="t1", user_id="u1")
    # First call fails, second succeeds
    mock_provider.call = AsyncMock(side_effect=[
        Exception("Temp error"),
        LlmResponse(content="Recovered", stop_reason="end_turn")
    ])
    
    response = await gateway.call(ctx, "sys", [], [], "gpt-4o", 100)
    assert response.content == "Recovered"
    assert mock_provider.call.call_count == 2

@pytest.mark.asyncio
async def test_llm_gateway_exhaust_retries(gateway, mock_provider):
    ctx = AgentContext(request_id="r1", agent_id="a1", tenant_id="t1")
    mock_provider.call = AsyncMock(side_effect=Exception("Perm error"))
    
    with pytest.raises(LLMUnavailableError):
        await gateway.call(ctx, "sys", [], [], "gpt-4o", 100)
    
    # max_retries=1 means 1 attempt + 1 retry = 2 total
    assert mock_provider.call.call_count == 2
