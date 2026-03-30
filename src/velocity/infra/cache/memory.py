"""
In-memory Cache Backend.
Zero-dependency ephemeral storage primarily optimized for `velocity dev` flows and testing.
State is lost immediately on process termination.
"""

import time

from velocity.infra import ICacheBackend


class MemoryCache(ICacheBackend):
    """
    Implements ICacheBackend using a standard Python dictionary.
    Includes naive garbage collection tracking TTLs passively on read access.
    """

    def __init__(self) -> None:
        # Maps key -> (value, expiration_timestamp_or_none)
        self._store: dict[str, tuple[str, float | None]] = {}

    def _is_expired(self, key: str) -> bool:
        if key not in self._store:
            return True
        _, expires_at = self._store[key]
        if expires_at is not None and time.time() > expires_at:
            # Passive GC
            del self._store[key]
            return True
        return False

    async def get(self, key: str) -> str | None:
        if self._is_expired(key):
            return None
        return self._store[key][0]

    async def set(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        expires_at = time.time() + ttl_seconds if ttl_seconds is not None else None
        self._store[key] = (value, expires_at)

    async def delete(self, key: str) -> bool:
        if self._is_expired(key):
            return False
        del self._store[key]
        return True

    async def health_check(self) -> bool:
        # Memory is always healthy if the process is running
        return True
