"""
Memory models ensuring standard formatting across persistence layers.
"""

from dataclasses import dataclass, field


@dataclass(slots=True)
class MemoryEntry:
    """
    Normalized structure representing an extracted piece of semantic state or 
    a historical message block.
    """
    id: str
    role: str                       # 'user', 'assistant', 'system', 'tool'
    content: str
    
    # Required for scoping multitenancy securely
    tenant_id: str
    agent_id: str 
    session_id: str | None = None
    
    # Metadata for filtering and recall
    timestamp: float = 0.0
    embedding: list[float] | None = field(default=None, repr=False)
    tags: dict[str, str] = field(default_factory=dict)
    
    @property
    def is_short_term(self) -> bool:
        """Indicates this is a highly volatile conversation block."""
        return self.session_id is not None
