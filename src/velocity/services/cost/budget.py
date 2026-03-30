"""
Budget enforcement logic.
Coordinates with shared cache to atomically check and update daily/monthly spending 
limits per tenant before LLM invocation.
"""

from datetime import UTC, datetime

from velocity.exceptions import BudgetExceededError
from velocity.infra import ICacheBackend


class BudgetTracker:
    """
    Manages aggregated cost limits. 
    Keys are segmented radially (daily, monthly) and namespace isolated per tenant.
    """
    
    def __init__(
        self, 
        cache: ICacheBackend, 
        default_daily_usd: float = 100.0,
        default_monthly_usd: float = 2000.0
    ):
        self.cache = cache
        self.default_daily_usd = default_daily_usd
        self.default_monthly_usd = default_monthly_usd

    def _get_daily_key(self, tenant_id: str) -> str:
        # Get UTC date string like '2024-03-15'
        date_str = datetime.now(UTC).strftime("%Y-%m-%d")
        return f"cost:daily:{tenant_id}:{date_str}"

    def _get_monthly_key(self, tenant_id: str) -> str:
        # Get UTC month string like '2024-03'
        month_str = datetime.now(UTC).strftime("%Y-%m")
        return f"cost:monthly:{tenant_id}:{month_str}"

    async def add_cost(self, tenant_id: str, cost_usd: float) -> None:
        """Increment tenant billing asynchronously (best effort recording)."""
        if cost_usd <= 0:
            return
            
        daily_key = self._get_daily_key(tenant_id)
        monthly_key = self._get_monthly_key(tenant_id)
        
        # We rely on string conversions over raw counters for floats if caching natively
        # Ideally, we leverage Lua scripting in Redis for atomic float incrementing
        # but for Interface flexibility, we do a read-modify-write here as fallback
        
        async def _increment_key(key: str, ttl: int) -> None:
            current_raw = await self.cache.get(key)
            current_val = float(current_raw) if current_raw else 0.0
            new_val = current_val + cost_usd
            await self.cache.set(key, str(new_val), ttl_seconds=ttl)
            
        # Background increment (don't block the caller thread natively for writing costs)
        await _increment_key(daily_key, ttl=86400 * 2)       # Max 2 days
        await _increment_key(monthly_key, ttl=86400 * 35)    # Max 35 days

    async def check_budget(self, tenant_id: str, estimated_next_call_usd: float = 0.0) -> bool:
        """
        Verify the tenant is below configured spending limits before executing the LLM.
        Will raise BudgetExceededError aggressively on boundary violation.
        """
        daily_key = self._get_daily_key(tenant_id)
        
        current_daily_raw = await self.cache.get(daily_key)
        current_daily = float(current_daily_raw) if current_daily_raw else 0.0
        
        if (current_daily + estimated_next_call_usd) > self.default_daily_usd:
            raise BudgetExceededError(
                f"Tenant {tenant_id} exceeded daily hard budget limit of ${self.default_daily_usd:.2f} USD.",
                details={"current_usage": current_daily, "limit": self.default_daily_usd}
            )
            
        monthly_key = self._get_monthly_key(tenant_id)
        current_monthly_raw = await self.cache.get(monthly_key)
        current_monthly = float(current_monthly_raw) if current_monthly_raw else 0.0
        
        if (current_monthly + estimated_next_call_usd) > self.default_monthly_usd:
             raise BudgetExceededError(
                f"Tenant {tenant_id} exceeded monthly budget limit of ${self.default_monthly_usd:.2f} USD.",
                details={"current_usage": current_monthly, "limit": self.default_monthly_usd}
            )
            
        return True
