"""
S3-backed Audit Storage.
Implementation of IAuditBackend using an Object Store for WORM compliance.
"""

import json
import logging
from typing import Any

from velocity.infra import IObjectStore
from velocity.services.audit.backends.base import IAuditBackend

logger = logging.getLogger(__name__)


class S3AuditBackend(IAuditBackend):
    """
    WORM-style (Write Once Read Many) Audit storage using object stores.
    Provides immutable, non-repudiable interaction records for compliance.
    """

    def __init__(self, object_store: IObjectStore, bucket_prefix: str = "audit"):
        self.object_store = object_store
        self.bucket_prefix = bucket_prefix

    async def write_record(self, record: dict[str, Any]) -> None:
        """
        Store a JSON blob to a directory-like structure: audit/{tenant_id}/{agent_id}/{request_id}.json
        """
        tenant_id = record.get("tenant_id", "default")
        agent_id = record.get("agent_id", "default")
        request_id = record.get("request_id", "default")
        
        object_key = f"{self.bucket_prefix}/{tenant_id}/{agent_id}/{request_id}.json"
        
        try:
            payload_bytes = json.dumps(record).encode("utf-8")
            await self.object_store.put_object(
                object_key, 
                payload_bytes, 
                content_type="application/json"
            )
        except Exception as e:
            logger.error(f"Audit S3 WORM upload failure for {request_id}: {e}")
            raise

    async def query_records(self, tenant_id: str, agent_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        """
        S3 is not optimized for ad-hoc queries.
        This implementation returns an empty list or requires a specialized index.
        For production, use the PostgresAuditBackend for queries and S3 for compliance archiving.
        """
        logger.warning(f"Querying S3 directly for audit records is not supported. Use Postgres audit instead.")
        return []

    async def health_check(self) -> bool:
        """Verify object store reachability."""
        return await self.object_store.health_check()
