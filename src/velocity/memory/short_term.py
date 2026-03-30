"""
Short-Term Memory Manager.
Uses the Redis/In-Memory Cache underlying infrastructure layer to preserve 
high-frequency conversation session state across stateless agent API invocations.
"""

import json
import logging
from typing import Any

from velocity.infra import ICacheBackend

logger = logging.getLogger(__name__)


class ShortTermMemoryManager:
    """
    Manages conversational throughput iteratively.
    Automatically pushes, pops, and retrieves conversation history matching LLM messaging specs.
    Handles pruning to stay within allocated LLM context window budgets implicitly.
    """

    def __init__(
        self, 
        cache: ICacheBackend, 
        default_ttl: int = 3600,   # 1 hour 
        max_messages: int = 50     # Pruning bounds
    ):
        self.cache = cache
        self.default_ttl = default_ttl
        self.max_messages = max_messages

    def _get_key(self, tenant_id: str, session_id: str) -> str:
        """Isolated tenant prefix mapping resolving to conversation keys."""
        return f"mem:short:{tenant_id}:{session_id}"

    async def load(self, tenant_id: str, session_id: str) -> list[dict[str, Any]]:
        """
        Pull the latest session history back into LLM memory representations.
        Returns a list of messages formatted according to standard dicts (role, content).
        """
        key = self._get_key(tenant_id, session_id)
        raw_data = await self.cache.get(key)
        
        if not raw_data:
            return []
            
        try:
            messages = json.loads(raw_data)
            return messages if isinstance(messages, list) else []
        except Exception as e:
            logger.error(f"Memory corruption resolving session {session_id} for tenant {tenant_id}: {e}")
            # Failsafe: return empty history rather than bricking the agent entirely
            return []

    async def save(self, tenant_id: str, session_id: str, messages: list[dict[str, Any]]) -> None:
        """
        Store conversation output deterministically, applying rolling pruning logic 
        if max message thresholds are exceeded.
        """
        if not messages:
            return
            
        # Hard pruning: keep only the most recent 'max_messages' to avoid token limit explosions
        if len(messages) > self.max_messages:
            logger.debug(f"Pruning short term memory for session {session_id} (Length: {len(messages)} -> {self.max_messages})")
            
            # Generally, we shouldn't slice out the very first system prompt or tool directives abruptly
            # but usually the Engine appends the system prompt independently of short-term state, 
            # so `messages` here represents only the pure dynamic conversation stack.
            messages = messages[-self.max_messages:]
            
        key = self._get_key(tenant_id, session_id)
        
        try:
            serialized_payload = json.dumps(messages)
            
            # Rolling TTL: every new message extends the conversation window
            await self.cache.set(key, serialized_payload, ttl_seconds=self.default_ttl)
            
        except TypeError as e:
            logger.error(f"Could not serialize conversational memory for {key}: {e}")
            raise

    async def clear(self, tenant_id: str, session_id: str) -> bool:
        """Explicitly reset a conversational node if requested by the Agent or User."""
        key = self._get_key(tenant_id, session_id)
        return await self.cache.delete(key)
