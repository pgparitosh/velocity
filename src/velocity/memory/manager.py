"""
Unified Memory Management facade.
Agents rarely deal with caching natively. The `MemoryManager` aggregates explicit
invocations or automated context threading globally.
"""

from typing import Any

from velocity.core.context import AgentContext
from velocity.memory.episodic import EpisodicMemoryManager
from velocity.memory.long_term import LongTermMemoryManager
from velocity.memory.short_term import ShortTermMemoryManager

class MemoryManager:
    """
    Primary interface for reading and writing multi-layered memory structures.
    Coordinates between highly volatile Redis stores and vector-backed semantic histories.
    """

    def __init__(
        self, 
        short_term: ShortTermMemoryManager | None = None,
        long_term: LongTermMemoryManager | None = None,
        episodic: EpisodicMemoryManager | None = None
    ):
        self.short_term = short_term
        self.long_term = long_term
        self.episodic = episodic

    async def initialize_session_context(self, ctx: AgentContext, initial_payload: str) -> list[dict[str, Any]]:
        """
        Pull conversational history and weave it with a new payload if session tracking is active.
        """
        messages = []
        if self.short_term and ctx.session_id:
            historical = await self.short_term.load(ctx.tenant_id, ctx.session_id)
            messages.extend(historical)
            
        messages.append({"role": "user", "content": initial_payload})
        return messages

    async def persist_session_context(self, ctx: AgentContext, messages: list[dict[str, Any]]) -> None:
        """
        Finalize a turn, capturing the updated dialog stack into highly-available caching tiers.
        """
        if self.short_term and ctx.session_id:
            await self.short_term.save(ctx.tenant_id, ctx.session_id, messages)

    async def inject_semantic_context(self, ctx: AgentContext, queries: list[str]) -> str:
        """
        Search vector persistence for long-term facts mapping to the current dialogue state.
        Returns a formatted knowledge block ready to be appended to system instructions natively.
        """
        if not self.long_term:
            return ""
           
        knowledge_blocks = []
        for query in queries:
            block = await self.long_term.format_knowledge_context(ctx.agent_id, query)
            if block:
                knowledge_blocks.append(block)
                
        return "\n".join(knowledge_blocks)
