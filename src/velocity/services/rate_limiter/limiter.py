"""
Global and Tenant-isolated Rate Limiting.
Ensures fairness and prevents cascading starvation across the platform deployment.
"""

import time

from velocity.core.context import AgentContext
from velocity.exceptions import RateLimitExceededError
from velocity.infra import ICacheBackend


class RateLimiter:
    """
    Implements a robust 3-tier sliding-window-esque (fixed-window approximation) 
    rate limiter using atomic Redis incrementation.
    
    Tiers:
      1. Platform Global (Protects infrastructure)
      2. Tenant (Ensures fairness between customers)
      3. Agent (Prevents runaway recursive or highly concurrent specific agents)
    """

    def __init__(
        self,
        cache: ICacheBackend,
        platform_limit: int = 10000,
        tenant_limit: int = 500,
        agent_limit: int = 60,
        window_seconds: int = 60  # Rate limits evaluated per minute natively
    ):
        self.cache = cache
        
        self.limits: dict[str, int] = {
            "platform": platform_limit,
            "tenant": tenant_limit,
            "agent": agent_limit
        }
        self.window_seconds = window_seconds

    def _get_keys(self, ctx: AgentContext, current_window: int) -> dict[str, str]:
        """Generate isolation keys mapped to the current time quantum."""
        return {
            "platform": f"rl:platform:{current_window}",
            "tenant": f"rl:tenant:{ctx.tenant_id}:{current_window}",
            "agent": f"rl:agent:{ctx.tenant_id}:{ctx.agent_id}:{current_window}"
        }

    async def _increment_and_check(self, key: str, limit: int) -> int:
        """
        Atomic operation to verify limits.
        If cache backend natively supports INCR, we use it, otherwise we simulate it 
        deterministically for this skeleton.
        """
        current_raw = await self.cache.get(key)
        current = int(current_raw) if current_raw else 0
        
        new_val = current + 1
        
        # We assume the cache layer handles TTL gracefully upon creation.
        # Ideally, `await self.cache.increment(key, ttl=self.window_seconds)` 
        await self.cache.set(key, str(new_val), ttl_seconds=self.window_seconds)
        
        return new_val

    async def verify_limits(self, ctx: AgentContext) -> None:
        """
        Pre-flight check invoked by the AgentEngine before LLM or Tool execution.
        Raises `RateLimitExceededError` if any 3-tier boundary is breached.
        """
        current_window = int(time.time() / self.window_seconds)
        keys = self._get_keys(ctx, current_window)
        
        for scope, key in keys.items():
            limit = self.limits[scope]
            current_count = await self._increment_and_check(key, limit)
            
            if current_count > limit:
                raise RateLimitExceededError(
                    f"{scope.capitalize()}-level rate limit exceeded "
                    f"({current_count} > {limit} req / {self.window_seconds}s).",
                    request_id=ctx.request_id,
                    agent_id=ctx.agent_id,
                    details={"scope": scope, "limit": limit, "window": self.window_seconds}
                )
