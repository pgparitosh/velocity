import uuid

import pytest

from velocity.infra.vector_store.simple import SimpleVectorStore
from velocity.memory.embedder import MockEmbedder
from velocity.memory.long_term import LongTermMemoryManager
from velocity.memory.models import MemoryEntry


@pytest.fixture
def ltm_manager():
    embedder = MockEmbedder(dimension=1536)
    vector_store = SimpleVectorStore()
    return LongTermMemoryManager(embedder, vector_store)

@pytest.mark.asyncio
async def test_add_and_recall_memory(ltm_manager):
    # 1. Add a memory
    entry = MemoryEntry(
        id=str(uuid.uuid4()),
        role="assistant",
        content="The user's favorite color is electric blue.",
        tenant_id="t1",
        agent_id="a1",
        timestamp=100.0
    )
    await ltm_manager.add_memory(entry)
    
    # 2. Recall it
    query = "What is the user's favorite color?"
    results = await ltm_manager.recall_memories(agent_id="a1", query=query)
    
    assert len(results) > 0
    assert "electric blue" in results[0].content
    assert results[0].agent_id == "a1"

@pytest.mark.asyncio
async def test_format_knowledge_context(ltm_manager):
    entry = MemoryEntry(
        id="m1",
        role="assistant",
        content="User lives in Zurich.",
        tenant_id="t1",
        agent_id="a1"
    )
    await ltm_manager.add_memory(entry)
    
    context = await ltm_manager.format_knowledge_context(agent_id="a1", query="location")
    assert "Zurich" in context
    assert "### RELEVANT KNOWLEDGE" in context
