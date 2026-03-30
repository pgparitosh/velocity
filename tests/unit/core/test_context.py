from velocity.core.context import AgentContext


def test_agent_context_initialization():
    # AgentContext(request_id, agent_id, tenant_id, session_id=None)
    ctx = AgentContext(request_id="req-abc", agent_id="agent-007", tenant_id="tenant-123")
    assert ctx.tenant_id == "tenant-123"
    assert ctx.request_id == "req-abc"
    assert ctx.agent_id == "agent-007"
    assert ctx.cost_usd == 0.0
    assert ctx.total_input_tokens == 0
    assert ctx.total_output_tokens == 0

def test_agent_context_record_llm_call():
    ctx = AgentContext(request_id="r1", agent_id="a1", tenant_id="t1")
    ctx.record_llm_call(
        model="gpt-4o",
        input_tokens=100,
        output_tokens=50,
        call_cost_usd=0.005,
        latency_ms=150.0
    )
    
    assert ctx.total_input_tokens == 100
    assert ctx.total_output_tokens == 50
    assert ctx.cost_usd == 0.005
    assert len(ctx.llm_calls) == 1
    assert ctx.llm_calls[0]["model"] == "gpt-4o"

def test_agent_context_record_tool_call():
    ctx = AgentContext(request_id="r1", agent_id="a1", tenant_id="t1")
    ctx.record_tool_call(
        tool_name="get_weather",
        success=True,
        latency_ms=50.0
    )
    
    assert len(ctx.tool_calls) == 1
    assert ctx.tool_calls[0]["tool_name"] == "get_weather"
    assert ctx.tool_calls[0]["success"] is True

def test_agent_context_metadata():
    ctx = AgentContext(request_id="r1", agent_id="a1", tenant_id="t1")
    ctx.tags["user_tier"] = "premium"
    assert ctx.tags.get("user_tier") == "premium"
