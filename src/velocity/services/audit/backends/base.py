"""
Abstract base for audit backends.
Decouples the AuditLogger from raw infrastructure implementations.
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class IAuditBackend(Protocol):
    """
    Interface for specialized audit storage.
    Ensures immutable recording of agent interactions.
    """

    async def write_record(self, record: dict[str, Any]) -> None:
        """
        Write a normalized audit record to the backend.
        
        Args:
            record: The dictionary representation of the Audit record.
        """
        ...

    async def query_records(self, tenant_id: str, agent_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        """
        Retrieve audit records for a specific tenant.
        """
        ...

    async def health_check(self) -> bool:
        """Verify the audit storage is reachable."""
        ...
