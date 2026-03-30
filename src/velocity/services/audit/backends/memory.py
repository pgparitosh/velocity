"""
In-Memory Audit Storage.
Implementation of IAuditBackend for local development and unit testing.
"""

from typing import Any
from velocity.services.audit.backends.base import IAuditBackend


class MemoryAuditBackend(IAuditBackend):
    """
    A simple in-memory list which serves as a volatile audit store.
    """

    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    async def write_record(self, record: dict[str, Any]) -> None:
        """
        Append a record to the memory store.
        """
        self.records.append(record)

    async def query_records(self, tenant_id: str, agent_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        """
        Filter records in memory by tenant_id and optionally agent_id.
        Returns the top-k most recent records.
        """
        filtered = [
            r for r in self.records 
            if r.get("tenant_id") == tenant_id and (agent_id is None or r.get("agent_id") == agent_id)
        ]
        # Return newest first
        return sorted(filtered, key=lambda x: x.get("start_time", 0.0), reverse=True)[:limit]

    async def health_check(self) -> bool:
        """Always healthy."""
        return True
