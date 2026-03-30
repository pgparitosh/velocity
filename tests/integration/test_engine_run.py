from unittest.mock import AsyncMock, MagicMock

import pytest

from velocity.core.base import AgentBase
from velocity.core.context import AgentContext
from velocity.core.engine import AgentEngine
from velocity.core.llm_gateway import LLMGateway, LlmResponse


class ComplexMockAgent(AgentBase):
    AGENT_ID = "complex-mock"
    
    def system_prompt(self): return "sys"
    def tools(self): return [{"name": "calc"}]
    
    async def execute_tool(self, name, inputs, ctx):
        if name == "calc":
            return str(inputs.get("a", 0) + inputs.get("b", 0))
        return "error"

@pytest.fixture
def engine():
    mock_gateway = MagicMock(spec=LLMGateway)
    return AgentEngine(llm_gateway=mock_gateway)

@pytest.mark.asyncio
async def test_engine_full_loop_with_tool(engine):
    agent = ComplexMockAgent()
    
    # 1. LLM asks to calc 1+2
    # 2. Engine calls agent.execute_tool("calc", {"a":1, "b":2}) -> returns "3"
    # 3. LLM receives "3" and provides final answer "3"
    
    engine.llm_gateway.call = AsyncMock(side_effect=[
        LlmResponse(
            content="", 
            stop_reason="tool_use", 
            tool_calls=[{"id": "call_1", "name": "calc", "inputs": {"a": 1, "b": 2}}]
        ),
        LlmResponse(
            content="The answer is 3", 
            stop_reason="end_turn"
        )
    ])
    
    result = await engine.run(
        agent=agent,
        payload="What is 1+2?",
        tenant_id="t1",
        request_id="r1"
    )
    
    assert "3" in result
    assert engine.llm_gateway.call.call_count == 2
    
    # Check that context was updated
    # We can't easily get the context since it's local to run(), 
    # but we can verify the mock was called with it.
    last_call_args = engine.llm_gateway.call.call_args_list[0]
    ctx = last_call_args.kwargs['ctx']
    assert isinstance(ctx, AgentContext)
    assert ctx.tenant_id == "t1"
    # Cost and tokens should be tracked if LlmResponse had them
