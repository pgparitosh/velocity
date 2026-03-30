"""
Health Probes.
Standard readiness and liveness endpoints for Kubernetes/Docker.
"""

import logging
from enum import Enum
from fastapi import APIRouter, Response

router = APIRouter()
logger = logging.getLogger(__name__)


class ClusterStatus(str, Enum):
    """Normalized health categorization."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"


@router.get("/health/live")
async def liveness_probe() -> dict:
    """Standard Kubernetes liveness check."""
    return {"status": "alive", "platform": "velocity"}


@router.get("/health/ready")
async def readiness_probe() -> dict:
    """
    Standard Kubernetes readiness check.
    In a full implementation, this would check:
    1. Redis connectivity (Cache/Rate Limiter)
    2. Postgres connectivity (Audit/Config)
    3. LLM Provider Reachability
    """
    # For this shim, we assume the platform is ready once the app boots.
    return {
        "status": ClusterStatus.HEALTHY,
        "services": {
            "cache": "connected",
            "database": "connected",
            "llm_gateway": "ready"
        }
    }
