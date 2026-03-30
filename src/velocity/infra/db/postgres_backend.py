"""
PostgreSQL Database Backend.
Production-grade persistence mapping raw queries asynchronously for Audit layers 
and high-throughput concurrent agent configuration storage.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

try:
    import asyncpg  # type: ignore[import-untyped]
    _asyncpg_available = True
except ImportError:
    _asyncpg_available = False

from velocity.infra import IDatabaseBackend


class PostgresBackend(IDatabaseBackend):
    """
    Implements standard SQL persistence relying on PostgreSQL pool mapping.
    Ensures massive concurrent access for heavily orchestrated LLM DAGs securely.
    """

    def __init__(self, connection_string: str, pool_size: int = 15) -> None:
        if not _asyncpg_available:
            raise ImportError("Please install `asyncpg` to use PostgreSQL backend.")
        
        self.dsn = connection_string
        self.pool_size = pool_size
        self._pool: Any = None  # asyncpg.Pool when initialized

    async def _get_pool(self) -> Any:
        """Lazy initialization of the connection pool."""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                dsn=self.dsn,
                min_size=2,
                max_size=self.pool_size
            )
        return self._pool

    def _convert_params(self, query: str, parameters: dict[str, Any]) -> tuple[str, list[Any]]:
        """
        asyncpg uses numeric positional arguments ($1, $2), whereas our protocol
        abstracts them as named parameters (`:request_id`).
        Converts named parameters to positional asyncpg format.
        """
        if not parameters:
            return query, []
            
        args: list[Any] = []
        for i, (key, value) in enumerate(parameters.items(), start=1):
            query = query.replace(f":{key}", f"${i}")
            args.append(value)
            
        return query, args

    async def execute(self, query: str, parameters: dict[str, Any] | None = None) -> None:
        pool = await self._get_pool()
        q, args = self._convert_params(query, parameters or {})
        async with pool.acquire() as connection:
            await connection.execute(q, *args)

    async def fetch_one(
        self, query: str, parameters: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        pool = await self._get_pool()
        q, args = self._convert_params(query, parameters or {})
        async with pool.acquire() as connection:
            record = await connection.fetchrow(q, *args)
            return dict(record) if record else None

    async def fetch_all(
        self, query: str, parameters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        pool = await self._get_pool()
        q, args = self._convert_params(query, parameters or {})
        async with pool.acquire() as connection:
            records = await connection.fetch(q, *args)
            return [dict(r) for r in records]

    async def health_check(self) -> bool:
        try:
            pool = await self._get_pool()
            async with pool.acquire() as connection:
                await connection.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"PostgreSQL Health Check Failed: {e}")
            return False

    async def close(self) -> None:
        """Gracefully drain the connection pool."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
