"""
PostgreSQL-backed Audit Storage.
Implementation of IAuditBackend using a relational database.
"""

import json
import logging
from typing import Any

from velocity.infra import IDatabaseBackend
from velocity.services.audit.backends.base import IAuditBackend

logger = logging.getLogger(__name__)


class PostgresAuditBackend(IAuditBackend):
    """
    Relational implementation of Audit storage.
    Optimized for fast queries and structured filtering.
    """

    def __init__(self, db: IDatabaseBackend, table_name: str = "velocity_audit_logs"):
        self.db = db
        self.table_name = table_name

    async def write_record(self, record: dict[str, Any]) -> None:
        """
        INSERT normalized context state into the audit table.
        """
        query = f"""
        INSERT INTO {self.table_name}
        (request_id, tenant_id, agent_id, status, cost_usd, timestamp, payload) 
        VALUES (:request_id, :tenant_id, :agent_id, :status, :cost_usd, CURRENT_TIMESTAMP, :payload)
        """
        try:
            # We serialize the entire record to JSONB for future-proofing
            payload_json = json.dumps(record)
            
            parameters = {
                "request_id": record.get("request_id"),
                "tenant_id": record.get("tenant_id"),
                "agent_id": record.get("agent_id"),
                "status": record.get("status", "UNKNOWN"),
                "cost_usd": record.get("metrics", {}).get("cost_usd", 0.0),
                "payload": payload_json
            }
            await self.db.execute(query, parameters)
        except Exception as e:
            logger.error(f"Audit DB write failure for {record.get('request_id')}: {e}")
            raise

    async def query_records(self, tenant_id: str, agent_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        """
        Perform a filtered search for audit records matching a tenant and optionally an agent.
        """
        query = f"SELECT payload FROM {self.table_name} WHERE tenant_id = :tenant_id"
        parameters = {"tenant_id": tenant_id}
        
        if agent_id:
            query += " AND agent_id = :agent_id"
            parameters["agent_id"] = agent_id
            
        query += f" ORDER BY timestamp DESC LIMIT {limit}"
        
        try:
            rows = await self.db.fetch_all(query, parameters)
            return [json.loads(row["payload"]) for row in rows]
        except Exception as e:
            logger.error(f"Audit DB query failure for tenant {tenant_id}: {e}")
            return []

    async def health_check(self) -> bool:
        """Verify database reachability."""
        return await self.db.health_check()
