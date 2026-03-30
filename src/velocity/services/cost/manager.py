"""
CostManager aggregation service.
Wraps routing, budget enforcement, and cost calculations under one cohesive facade 
used natively by the AgentEngine pre and post flight hooks.
"""


from velocity.core.context import AgentContext
from velocity.infra import ICacheBackend

from .budget import BudgetTracker
from .routing import DEFAULT_ROUTING_RULES, resolve_model_override


class CostManager:
    """
    Platform-wide service governing financial boundaries.
    Responsible for checking budget solvency before LLM invocation, routing to the 
    most cost-efficient backend, and asynchronously recording post-flight usage statistics 
    per-tenant seamlessly.
    """

    def __init__(self, cache: ICacheBackend):
        self.budget_tracker = BudgetTracker(cache)
        
    async def pre_flight_check(self, context: AgentContext) -> None:
        """
        Verify tenant solvency prior to deep agent execution.
        Raises `BudgetExceededError` if boundaries violated.
        """
        await self.budget_tracker.check_budget(context.tenant_id)

    def route_model(self, context: AgentContext, default_model: str) -> str:
        """
        Derive the most optimized model strictly based on runtime context tags,
        potentially downgrading to Haiku or upgrading to o1 based on rules.
        """
        return resolve_model_override(context, default_model, DEFAULT_ROUTING_RULES)

    async def post_flight_record(self, context: AgentContext) -> None:
        """
        Aggregate total runtime usages derived from the Context iteration 
        and flush them atomically backend for financial reconciliation.
        """
        
        # The engine context already contains total usd accumulated per discrete tool/llm step.
        # However, as a failsafe or for audit-level precision, we re-verify or simply push the sum.
        final_cost = context.cost_usd
        
        # We push asynchronously to not block the final client HTTP response
        await self.budget_tracker.add_cost(context.tenant_id, final_cost)
