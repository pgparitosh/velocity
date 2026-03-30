"""
Central Prompt Library caching and resolution layer.
Enables agents to request system prompts by reference (e.g., 'fraud-agent@v2.3.0'),
with variables substituted at runtime, bypassing external I/O via aggressive caching.
"""

import json
import logging
from typing import Any

from velocity.infra import ICacheBackend

from .backends.base import IPromptBackend
from .models import PromptVersion
from .renderer import render_prompt

logger = logging.getLogger(__name__)


class PromptLibrary:
    """
    Tiered caching system for immutable prompt assets ensuring near zero-latency 
    resolutions for hot-path agent invocations.
    
    Tiers:
      L1: In-memory dictionary (Shared across requests on this node)
      L2: Redis (Shared across platform deployment nodes via ICacheBackend)
      L3: Storage Backend (S3/Filesystem via IPromptBackend)
    """

    def __init__(
        self, 
        storage_backend: IPromptBackend, 
        cache_backend: ICacheBackend | None = None,
        # Default TTL for Redis L2 cache if utilized (e.g., 24 hours)
        l2_ttl_seconds: int = 86400 
    ):
        self.storage = storage_backend
        self.cache = cache_backend
        self.l2_ttl = l2_ttl_seconds
        
        # Local L1 node cache: mapping fully qualified references -> PromptVersion
        self._l1_cache: dict[str, PromptVersion] = {}

    def _parse_reference(self, reference: str) -> tuple[str, str]:
        """Split 'agent_name@v1.2' into ('agent_name', 'v1.2'). Defaults to 'latest'."""
        if "@" in reference:
            parts = reference.split("@", 1)
            return parts[0], parts[1]
        return reference, "latest"

    async def _resolve_prompt_version(self, prompt_id: str, version: str) -> PromptVersion:
        """
        Traverse the latency hierarchy (L1 -> L2 -> L3) to locate a prompt safely.
        """
        fqn = f"{prompt_id}@{version}"
        
        # 1. Check L1 Memory (Instant)
        if fqn in self._l1_cache:
            return self._l1_cache[fqn]
            
        # 2. Check L2 Redis/Network Cache (Microseconds)
        if self.cache:
            cache_hit = await self.cache.get(f"prompt:{fqn}")
            if cache_hit:
                # We deserialize and populate L1 retrospectively
                try:
                    data = json.loads(cache_hit)
                    prompt_ver = PromptVersion(**data)
                    self._l1_cache[fqn] = prompt_ver
                    return prompt_ver
                except Exception as e:
                    logger.warning(f"L2 Prompt cache corrupted for {fqn}: {e}. Falling through to L3.")

        # 3. Check L3 Storage Backend (Milliseconds - AWS S3, etc.)
        prompt_ver = await self.storage.fetch(prompt_id, version)
        
        # Hydrate caches upward
        self._l1_cache[fqn] = prompt_ver
        if self.cache:
            try:
                # Assuming dataclass converts directly to dict easily natively or via simple cast
                serialized = json.dumps(prompt_ver.__dict__)
                await self.cache.set(f"prompt:{fqn}", serialized, ttl_seconds=self.l2_ttl)
            except Exception as e:
                logger.error(f"Failed to populate L2 cache for prompt {fqn}: {e}")

        return prompt_ver

    async def resolve(self, reference: str, variables: dict[str, Any] | None = None) -> str:
        """
        The primary public interface for platform core.
        Takes a semantic reference string, resolves it to content, applies f-string mappings, 
        and returns the raw string instructions ready for an LLM Gateway payload.
        """
        prompt_id, version = self._parse_reference(reference)
        
        # Traverse cache tiers
        prompt_obj = await self._resolve_prompt_version(prompt_id, version)
        
        # Fast path if no dynamics applied
        if not variables:
            return prompt_obj.content
            
        # Execute rigorous variable interpolation
        return render_prompt(prompt_obj.content, variables)
