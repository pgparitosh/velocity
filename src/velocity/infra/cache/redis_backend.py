"""
Redis Cache Backend.
Production-grade ICacheBackend mapping to highly available sorted sets, hashes, and streams.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


try:
    import redis.asyncio as aioredis
    _redis_available = True
except ImportError:
    _redis_available = False

from velocity.infra import ICacheBackend


class RedisCache(ICacheBackend):
    """
    Standard Redis integration. 
    Powers the Rate Limiter, Cost Budgets, and Short-Term memory layers concurrently.
    """

    def __init__(self, url: str) -> None:
        if not _redis_available:
            raise ImportError("The 'redis' package is required to use RedisCache. Run `pip install redis`.")
        # Store client as Any since redis stubs may not be available
        self._client: Any = aioredis.from_url(url, decode_responses=True)

    async def get(self, key: str) -> str | None:
        result: Any = await self._client.get(key)
        return str(result) if result is not None else None

    async def set(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        await self._client.set(key, value, ex=ttl_seconds)

    async def delete(self, key: str) -> bool:
        deleted_count: Any = await self._client.delete(key)
        return bool(deleted_count > 0)

    async def health_check(self) -> bool:
        try:
            result: Any = await self._client.ping()
            return bool(result)
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False
