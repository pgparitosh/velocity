"""
Episodic Memory Manager.
Handles the storage and retrieval of past interaction outcomes (episodes).
Stored in Redis/In-Memory Cache with a cap on the number of episodes.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from velocity.infra import ICacheBackend

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class EpisodicEntry:
    """Represents a single interaction episode and its outcome."""
    summary: str
    outcome: str
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


class EpisodicMemoryManager:
    """
    Manages episodic memory - high-level summaries of past interactions.
    Helps agents learn from past outcomes without re-reading entire transcripts.
    """

    def __init__(
        self,
        cache: ICacheBackend,
        max_episodes: int = 100,
        ttl_seconds: int = 7776000  # 90 days
    ):
        self.cache = cache
        self.max_episodes = max_episodes
        self.ttl_seconds = ttl_seconds

    def _get_key(self, tenant_id: str, agent_id: str, user_id: str) -> str:
        """Scoped key for episodic memory."""
        return f"mem:episodic:{tenant_id}:{agent_id}:{user_id}"

    async def add_episode(
        self,
        tenant_id: str,
        agent_id: str,
        user_id: str,
        summary: str,
        outcome: str,
        metadata: dict[str, Any] | None = None
    ) -> None:
        """Add a new episode to the history, enforcing the max count limit."""
        key = self._get_key(tenant_id, agent_id, user_id)
        
        # Load existing episodes
        raw = await self.cache.get(key)
        episodes = []
        if raw:
            try:
                episodes = json.loads(raw)
            except Exception as e:
                logger.error(f"Failed to parse episodic memory for {key}: {e}")

        # Add new episode
        new_episode = {
            "summary": summary,
            "outcome": outcome,
            "timestamp": time.time(),
            "metadata": metadata or {}
        }
        episodes.insert(0, new_episode) # Newest first

        # Cap episodes
        if len(episodes) > self.max_episodes:
            episodes = episodes[:self.max_episodes]

        # Save back
        try:
            await self.cache.set(key, json.dumps(episodes), ttl_seconds=self.ttl_seconds)
        except Exception as e:
            logger.error(f"Failed to save episodic memory for {key}: {e}")

    async def get_episodes(
        self,
        tenant_id: str,
        agent_id: str,
        user_id: str,
        limit: int = 5
    ) -> list[EpisodicEntry]:
        """Retrieve the most recent episodes."""
        key = self._get_key(tenant_id, agent_id, user_id)
        raw = await self.cache.get(key)
        
        if not raw:
            return []
            
        try:
            data = json.loads(raw)
            return [
                EpisodicEntry(
                    summary=e["summary"],
                    outcome=e["outcome"],
                    timestamp=e.get("timestamp", 0.0),
                    metadata=e.get("metadata", {})
                )
                for e in data[:limit]
            ]
        except Exception as e:
            logger.error(f"Failed to load episodic memory for {key}: {e}")
            return []
