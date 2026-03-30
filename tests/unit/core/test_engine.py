from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from velocity.core.base import AgentBase
from velocity.core.context import AgentContext
from velocity.core.engine import AgentEngine
from velocity.core.llm_gateway import LLMGateway, LlmResponse


class MockAgent(AgentBase):
    AGENT_ID = "mock-agent"
    
    def system_prompt(self) -> str:
        return "You are a mock"
        
    def tools(self) -> list[dict[str, Any]]:
        return []
        
    async def execute_tool(self, name: str, inputs: dict[str, Any], ctx: AgentContext) -> Any:
        return "tool_result"

@pytest.fixture
def mock_gateway():
    return MagicMock(spec=LLMGateway)

@pytest.fixture
def engine(mock_gateway):
    # AgentEngine(llm_gateway, default_model="gpt-4o")
    return AgentEngine(llm_gateway=mock_gateway)

@pytest.mark.asyncio
async def test_engine_single_turn_no_tools(engine, mock_gateway):
    agent = MockAgent()
    mock_gateway.call = AsyncMock(return_value=LlmResponse(
        content="Final Answer", stop_reason="end_turn", input_tokens=10, output_tokens=5
    ))
    
    result = await engine.run(agent, "Hi", tenant_id="t1", request_id="r1")
    assert result == "Final Answer"
    assert mock_gateway.call.call_count == 1

@pytest.mark.asyncio
async def test_engine_with_tool_call(engine, mock_gateway):
    agent = MockAgent()
    # Override tools for this test
    agent.tools = MagicMock(return_value=[{"name": "get_x"}])
    
    # First call: LLM says use tool
    # Second call: LLM says final answer
    mock_gateway.call = AsyncMock(side_effect=[
        LlmResponse(
            content="", 
            stop_reason="tool_use", 
            tool_calls=[{"id": "c1", "name": "get_x", "inputs": {"val": 1}}]
        ),
        LlmResponse(
            content="The value is 100", 
            stop_reason="end_turn"
        )
    ])
    
    # Mock agent's execute_tool
    agent.execute_tool = AsyncMock(return_value="100")
    
    result = await engine.run(agent, "Give me X", tenant_id="t1", request_id="r1")
    assert result == "The value is 100"
    assert mock_gateway.call.call_count == 2
    assert agent.execute_tool.called
