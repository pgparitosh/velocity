
import pytest

from velocity.core.context import AgentContext
from velocity.exceptions import RateLimitExceededError
from velocity.infra.cache.memory import MemoryCache
from velocity.services.rate_limiter.limiter import RateLimiter


@pytest.fixture
def memory_cache():
    return MemoryCache()

@pytest.fixture
def rate_limiter(memory_cache):
    # Set low limits for testing: 10 requests per minute for agent
    return RateLimiter(cache=memory_cache, agent_limit=10)

@pytest.mark.asyncio
async def test_rate_limiter_allowed(rate_limiter):
    ctx = AgentContext(request_id="r1", agent_id="a1", tenant_id="t1")
    # Multiple calls within limit
    for _ in range(5):
        await rate_limiter.verify_limits(ctx)

@pytest.mark.asyncio
async def test_rate_limiter_blocked(rate_limiter):
    ctx = AgentContext(request_id="r1", agent_id="a1", tenant_id="t1")
    # 11th call should be blocked since limit is 10
    for _ in range(10):
        await rate_limiter.verify_limits(ctx)
    
    with pytest.raises(RateLimitExceededError):
        await rate_limiter.verify_limits(ctx)

@pytest.mark.asyncio
async def test_rate_limiter_independent_entities(rate_limiter):
    ctx_a = AgentContext(request_id="r1", agent_id="a1", tenant_id="t1")
    ctx_b = AgentContext(request_id="r1", agent_id="b1", tenant_id="t1")
    
    # Exhausting one agent shouldn't block another
    for _ in range(10):
        await rate_limiter.verify_limits(ctx_a)
    
    with pytest.raises(RateLimitExceededError):
        await rate_limiter.verify_limits(ctx_a)
    
    # Other agent should be fine
    await rate_limiter.verify_limits(ctx_b)
