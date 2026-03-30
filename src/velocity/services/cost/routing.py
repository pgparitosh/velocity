"""
Routing rules mapping logical agent intents to specific models safely.
Enforces cost savings automatically for rote tasks.
"""

from collections.abc import Callable

from velocity.core.context import AgentContext

# A rule is a tuple: (Condition checking the Context, Target Model Name)
RoutingRule = tuple[Callable[[AgentContext], bool], str]

# Default routing sequences prioritizing latency and cost for known patterns
DEFAULT_ROUTING_RULES: list[RoutingRule] = [
    # Quick text classification checks don't need Opus/4o
    (lambda ctx: ctx.tags.get("task_type") == "classification", "claude-3-5-haiku-latest"),
    
    # Simple semantic extraction is fine on mini models
    (lambda ctx: ctx.tags.get("task_type") == "extraction", "gpt-4o-mini"),
    
    # Deep reasoning/math requires specific capabilities
    (lambda ctx: ctx.tags.get("requires_reasoning") == "true", "o1-preview"),
]


def resolve_model_override(ctx: AgentContext, default_model: str, rules: list[RoutingRule] | None = None) -> str:
    """
    Evaluate routing rules top-to-bottom. 
    First match overrides the default model, returning the cheaper/specific substitute.
    """
    applied_rules = rules if rules is not None else DEFAULT_ROUTING_RULES
    
    for condition, target_model in applied_rules:
        try:
            if condition(ctx):
                return target_model
        except Exception:
            # Swallow exceptions in rule evaluations rather than crash the agent run
            pass
            
    return default_model
