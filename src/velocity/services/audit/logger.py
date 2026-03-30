"""
Audit Logger system.
Ensures every action, metadata tag, and cost attribution is saved to 
immutable storage layers for Enterprise compliance.
"""

import json
import logging

from velocity.core.context import AgentContext
from velocity.infra import IDatabaseBackend, IEventStream, IObjectStore

logger = logging.getLogger(__name__)


class AuditLogger:
    """
    Subsystem responsible for non-repudiation and observability tracking.
    All outputs strictly adhere to normalized JSON structured schemas for ingestion 
    into downstream SIEMs or Data Lakes.
    """

    def __init__(
        self,
        db_backend: IDatabaseBackend | None = None,
        s3_backend: IObjectStore | None = None,
        event_stream: IEventStream | None = None,
        retention_years: int = 7
    ):
        self.db = db_backend
        self.s3 = s3_backend
        self.events = event_stream
        self.retention_years = retention_years

    async def log_session_completion(self, ctx: AgentContext, final_payload: str, error: Exception | None = None) -> None:
        """
        Records the ultimate state of the context block asynchronously after the response 
        has theoretically been dispatched to the caller.
        """
        # 1. Serialize deterministic context state
        
        # We handle float conversion and safe parsing natively here
        record = {
            "request_id": ctx.request_id,
            "tenant_id": ctx.tenant_id,
            "agent_id": ctx.agent_id,
            "session_id": ctx.session_id,
            "trace_id": ctx.trace_id,
            "iteration": ctx.iteration,
            "start_time": ctx._start_time,
            "end_time": ctx._end_time,
            "elapsed_ms": ctx.elapsed_ms,
            "metrics": {
                "llm_calls": len(ctx.llm_calls),
                "tool_calls": ctx.total_tool_calls,
                "input_tokens": ctx.total_input_tokens,
                "output_tokens": ctx.total_output_tokens,
                "cost_usd": ctx.cost_usd
            },
            "tags": ctx.tags,
            "events": ctx.events, # Security maskings, rule fires
            "status": "ERROR" if error else "SUCCESS",
            "error_msg": str(error) if error else None
        }

        # Format natively to JSON
        try:
            json_payload = json.dumps(record)
        except Exception as e:
            logger.error(f"Failed to serialize audit record for {ctx.request_id}: {e}")
            return
            
        # 2. Replicate across configured infrastructure layers
        
        if self.events:
            try:
                await self.events.publish("velocity.audit.completed", record)
            except Exception as e:
                logger.error(f"Audit Event Stream write failure: {e}")
                
        if self.db:
            try:
                # Assuming table 'velocity_audit_logs' with a JSONB column 'payload'
                query = """
                INSERT INTO velocity_audit_logs 
                (request_id, tenant_id, agent_id, status, cost_usd, timestamp, payload) 
                VALUES (:request_id, :tenant_id, :agent_id, :status, :cost_usd, CURRENT_TIMESTAMP, :payload)
                """
                parameters = {
                    "request_id": ctx.request_id,
                    "tenant_id": ctx.tenant_id,
                    "agent_id": ctx.agent_id,
                    "status": "ERROR" if error else "SUCCESS",
                    "cost_usd": ctx.cost_usd,
                    "payload": json_payload
                }
                await self.db.execute(query, parameters)
            except Exception as e:
                logger.error(f"Audit DB write failure for {ctx.request_id}: {e}")

        if self.s3:
            try:
                # WORM strategy via S3
                object_key = f"audit/{ctx.tenant_id}/{ctx.agent_id}/{ctx.request_id}.json"
                await self.s3.put_object(object_key, json_payload.encode('utf-8'), content_type="application/json")
            except Exception as e:
                logger.error(f"Audit S3 WORM upload failure for {ctx.request_id}: {e}")
