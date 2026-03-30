"""
Stop conditions governing the main execution loops of Agents.
Designed to prevent agent starvation, infinite looping, and runaway LLM costs 
(a primary concern for production deployments).
"""

from dataclasses import dataclass

from velocity.core.context import AgentContext
from velocity.exceptions import BudgetExceededError, WorkflowTimeoutError


@dataclass(frozen=True, slots=True)
class StopConditions:
    """
    Configuration defining the outer bounds of an agent's execution.
    These constraints apply universally, regardless of the prompt or tools.
    """
    max_iterations: int = 25
    max_time_seconds: int | None = 300
    max_budget_usd: float | None = None


def check_stop_conditions(ctx: AgentContext, conditions: StopConditions) -> bool:
    """
    Validates the current state of an `AgentContext` against configured `StopConditions`.
    
    Returns:
        True if the agent should stop naturally (e.g., iterations reached max gracefully).
        Raises specific velocity exceptions if bounded limits like cost or time are violated.
    """
    if ctx.iteration > conditions.max_iterations:
        # Note: Depending on the specific platform design, exceeding max_iterations
        # could be an error, or just a graceful fallback (meaning the agent did its best).
        # We will treat it as a graceful stop, returning partial results.
        return True

    # Check timeout bounding
    if conditions.max_time_seconds is not None:
        elapsed = ctx.elapsed_ms / 1000.0
        if elapsed > conditions.max_time_seconds:
            raise WorkflowTimeoutError(
                f"Agent execution exceeded configured timeout of {conditions.max_time_seconds}s.",
                request_id=ctx.request_id,
                agent_id=ctx.agent_id,
                details={"elapsed_s": elapsed, "max_s": conditions.max_time_seconds}
            )

    # Check budget constraints
    if conditions.max_budget_usd is not None:
        if ctx.cost_usd > conditions.max_budget_usd:
            raise BudgetExceededError(
                f"Agent execution exceeded hard budget of ${conditions.max_budget_usd:.2f}.",
                request_id=ctx.request_id,
                agent_id=ctx.agent_id,
                details={"cost_usd": ctx.cost_usd, "max_budget_usd": conditions.max_budget_usd}
            )

    return False
