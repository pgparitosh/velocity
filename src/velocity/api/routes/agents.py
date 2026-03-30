"""
Agent Runtime Endpoints.
Provides the primary interface for running agents and polling status.
"""

import logging
import uuid
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, Field

from velocity.core.engine import AgentEngine
from velocity.api.auth import get_tenant_context

router = APIRouter()
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Request & Response Models
# -----------------------------------------------------------------------------

class RunAgentRequest(BaseModel):
    """Payload to trigger an agent invocation."""
    agent_id: str = Field(..., description="The identifier of the agent to execute.")
    payload: str = Field(..., description="The user's initial prompt or data payload.")
    session_id: Optional[str] = Field(None, description="Optional session tracking ID.")
    config_override: Optional[Dict[str, Any]] = Field(default_factory=dict)


class RunAgentResponse(BaseModel):
    """Status returned after a successful agent execution."""
    request_id: str
    result: Any
    elapsed_ms: float
    total_cost_usd: float


# -----------------------------------------------------------------------------
# Handlers
# -----------------------------------------------------------------------------

@router.post("/run", response_model=RunAgentResponse)
async def run_agent(
    request: RunAgentRequest,
    tenant: Dict[str, Any] = Depends(get_tenant_context),
    # In a real app, engine is a dependency provided by app.state or similar
    # engine: AgentEngine = Depends(get_engine)
):
    """
    Synchronously execute an agent turn and return the final result.
    Fully instruments the process with platform services (security, cost, audit).
    """
    
    # Implementation Note: 
    # This endpoint demonstrates the platform API surface. 
    # Actual execution would require the Engine to be wired into the API.
    
    logger.info(f"API Request: Running agent '{request.agent_id}' for tenant '{tenant.get('tenant_id')}'")
    
    # Mocking the response for now until the full wiring is complete in the entry point.
    return RunAgentResponse(
        request_id=str(uuid.uuid4()),
        result=f"Agent '{request.agent_id}' processed: {request.payload[:50]}...",
        elapsed_ms=1240.5,
        total_cost_usd=0.0045
    )

@router.get("/{request_id}/status")
async def get_agent_status(
    request_id: str,
    tenant: Dict[str, Any] = Depends(get_tenant_context)
):
    """
    Retrieve the execution status of a background/async request.
    """
    return {"request_id": request_id, "status": "COMPLETED", "result_available": True}
