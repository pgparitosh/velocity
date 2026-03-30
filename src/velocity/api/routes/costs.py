"""
Cost Distribution & Budget Reporting Endpoints.
Allows tenants to track their spend across agents, models, and features 
deterministically for billable attribution.
"""

import logging
from typing import Any, Dict
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from velocity.api.auth import get_tenant_context

router = APIRouter()
logger = logging.getLogger(__name__)


class CostReportResponse(BaseModel):
    """Normalized cost reporting response."""
    tenant_id: str
    total_cost_usd: float
    breakdown: Dict[str, float]
    budget_remaining: float


@router.get("/", response_model=CostReportResponse)
async def get_tenant_costs(
    days: int = 30,
    tenant: Dict[str, Any] = Depends(get_tenant_context)
):
    """
    Retrieve aggregated spend metrics for the calling tenant.
    """
    tenant_id = tenant.get("tenant_id", "unknown")
    
    # In a full implementation, we'd query the CostManager or a Time-series DB.
    # For this shim, we return a mock report.
    return CostReportResponse(
        tenant_id=tenant_id,
        total_cost_usd=12.45,
        breakdown={
            "expense-approver": 8.12,
            "fraud-analyst": 4.33
        },
        budget_remaining=487.55
    )
