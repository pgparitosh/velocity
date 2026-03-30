import asyncio

import pytest

from velocity.infra.cache.memory import MemoryCache


@pytest.mark.asyncio
async def test_memory_cache_get_set():
    cache = MemoryCache()
    await cache.set("foo", "bar")
    assert await cache.get("foo") == "bar"
    assert await cache.get("non-existent") is None

@pytest.mark.asyncio
async def test_memory_cache_ttl_expiration():
    cache = MemoryCache()
    # Set with 0.1s TTL
    await cache.set("short-lived", "val", ttl_seconds=0.1)
    assert await cache.get("short-lived") == "val"
    
    await asyncio.sleep(0.15)
    # Should be expired now
    assert await cache.get("short-lived") is None

@pytest.mark.asyncio
async def test_memory_cache_delete():
    cache = MemoryCache()
    await cache.set("to-delete", "x")
    assert await cache.delete("to-delete") is True
    assert await cache.get("to-delete") is None
    # Delete non-existent should be False
    assert await cache.delete("not-there") is False

@pytest.mark.asyncio
async def test_memory_cache_health_check():
    cache = MemoryCache()
    assert await cache.health_check() is True
