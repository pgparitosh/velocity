"""
Long-Term Semantic Memory Manager.
Uses embeddings and vector stores to persist and retrieve 
cross-session knowledge and facts.
"""

import uuid

from velocity.infra import IVectorStore
from velocity.memory.embedder import ITextEmbedder
from velocity.memory.models import MemoryEntry


class LongTermMemoryManager:
    """
    Manages semantic storage and retrieval of interaction history and injected facts.
    """

    def __init__(self, embedder: ITextEmbedder, vector_store: IVectorStore):
        self.embedder = embedder
        self.vector_store = vector_store

    async def add_memory(self, entry: MemoryEntry) -> None:
        """
        Embeds the entry content and indexes it into the permanent vector store.
        """
        vector = await self.embedder.embed_text(entry.content)
        
        # We index using a specific collection per agent to ensure isolation
        collection_name = f"agent_{entry.agent_id}_ltm"
        
        payload = {
            "id": entry.id,
            "role": entry.role,
            "content": entry.content,
            "tenant_id": entry.tenant_id,
            "agent_id": entry.agent_id,
            "session_id": entry.session_id,
            "timestamp": entry.timestamp,
            "tags": entry.tags
        }
        
        await self.vector_store.upsert(
            collection=collection_name,
            vector_id=entry.id or str(uuid.uuid4()),
            vector=vector,
            payload=payload
        )

    async def recall_memories(
        self, 
        agent_id: str, 
        query: str, 
        top_k: int = 5,
        min_score: float = 0.7
    ) -> list[MemoryEntry]:
        """
        Retrieves the top-k semantically relevant memories for a given query.
        """
        query_vector = await self.embedder.embed_text(query)
        collection_name = f"agent_{agent_id}_ltm"
        
        # Search returns payloads
        payloads = await self.vector_store.search(
            collection=collection_name,
            query_vector=query_vector,
            top_k=top_k
        )
        
        memories = []
        for p in payloads:
            memories.append(MemoryEntry(
                id=p["id"],
                role=p["role"],
                content=p["content"],
                tenant_id=p["tenant_id"],
                agent_id=p["agent_id"],
                session_id=p["session_id"],
                timestamp=p["timestamp"],
                tags=p["tags"]
            ))
            
        return memories

    async def format_knowledge_context(self, agent_id: str, query: str) -> str:
        """
        Retrieves relevant memories and formats them as a knowledge block 
        suitable for inclusion in a system prompt.
        """
        memories = await self.recall_memories(agent_id, query)
        if not memories:
            return ""
            
        block = "\n### RELEVANT KNOWLEDGE FROM PAST INTERACTIONS:\n"
        for mem in memories:
            block += f"- [{mem.role}]: {mem.content}\n"
        
        return block
