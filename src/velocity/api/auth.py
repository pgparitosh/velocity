"""
Security & Multi-tenancy Authentication.
Handles JWT token validation, tenant claim extraction, and identity resolution 
for platform API requests.
"""

import os
import logging
from typing import Any, Dict, Optional
from fastapi import Header, HTTPException, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)


# Mock Auth for Development
JWT_SECRET = os.environ.get("JWT_SECRET", "velocity_dev_secret")
security = HTTPBearer()

async def get_tenant_context(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> Dict[str, Any]:
    """
    Dependency to extract tenant identity and permissions from a JWT token.
    In production, this would use a library like `python-jose` to verify the signature.
    For the current platform shim, we rely on a simplified implementation.
    """
    token = credentials.credentials
    
    # In a full implementation: 
    # payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    # return payload
    
    # Mock behavior for local development/testing
    if token == "dev-token-admin":
        return {
            "tenant_id": "velocity-internal",
            "user_id": "admin-001",
            "permissions": ["*"]
        }
    
    if token.startswith("dev-token-"):
        tenant_name = token.split("-")[2]
        return {
            "tenant_id": f"tenant-{tenant_name}",
            "user_id": "user-001",
            "permissions": ["agent.run", "cost.read"]
        }

    raise HTTPException(status_code=401, detail="Invalid authorization token")


class TenantContext:
    """Convenience wrapper for the extracted tenant context."""
    def __init__(self, payload: Dict[str, Any]):
        self.tenant_id = payload.get("tenant_id", "anonymous")
        self.user_id = payload.get("user_id")
        self.permissions = payload.get("permissions", [])
