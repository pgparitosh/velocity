import pytest

from velocity.core.context import AgentContext
from velocity.core.stop_conditions import StopConditions, check_stop_conditions


def test_stop_conditions_initialization():
    sc = StopConditions(max_iterations=5, max_budget_usd=1.0, max_time_seconds=100)
    assert sc.max_iterations == 5
    assert sc.max_budget_usd == 1.0
    assert sc.max_time_seconds == 100

def test_stop_conditions_check_within_limits():
    sc = StopConditions(max_iterations=5, max_budget_usd=1.0, max_time_seconds=100)
    ctx = AgentContext(request_id="r1", agent_id="a1", tenant_id="t1")
    ctx.iteration = 4
    ctx.cost_usd = 0.5
    # check_stop_conditions returns True if we should stop, False if we should continue
    assert check_stop_conditions(ctx, sc) is False

def test_stop_conditions_check_exceed_iterations():
    sc = StopConditions(max_iterations=5)
    ctx = AgentContext(request_id="r1", agent_id="a1", tenant_id="t1")
    ctx.iteration = 6
    assert check_stop_conditions(ctx, sc) is True

def test_stop_conditions_check_exceed_budget():
    from velocity.exceptions import BudgetExceededError
    sc = StopConditions(max_budget_usd=0.1)
    ctx = AgentContext(request_id="r1", agent_id="a1", tenant_id="t1")
    ctx.cost_usd = 0.15
    with pytest.raises(BudgetExceededError):
        check_stop_conditions(ctx, sc)

def test_stop_conditions_check_exceed_time():
    from velocity.exceptions import WorkflowTimeoutError
    sc = StopConditions(max_time_seconds=1)
    ctx = AgentContext(request_id="r1", agent_id="a1", tenant_id="t1")
    # Simulate elapsed time by mocking or manually setting internal state if allowed
    # AgentContext calculates elapsed_ms using time.monotonic() - _start_time
    import time
    ctx._start_time = time.monotonic() - 2.0 # Force 2 seconds elapsed
    with pytest.raises(WorkflowTimeoutError):
        check_stop_conditions(ctx, sc)
