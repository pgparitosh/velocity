"""
Velocity Platform API.
Main FastAPI application entry point.
Registers routers, middleware, and exception handlers.
"""

import logging
from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from velocity.exceptions import VelocityError
from velocity.api.auth import get_tenant_context

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Initialize and configure the platform's REST API."""
    app = FastAPI(
        title="Velocity - AI Agent Platform",
        version="1.0.0",
        description="Scalable, production-ready horizontal infrastructure for AI agents."
    )

    # 1. Identity & Cross-Cutting Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Global Exception Handling
    @app.exception_handler(VelocityError)
    async def velocity_exception_handler(request: Request, exc: VelocityError):
        """Standardized JSON error formatting for all platform errors."""
        logger.error(f"Platform Error [{exc.__class__.__name__}]: {exc.message}")
        return JSONResponse(
            status_code=400, # Categorize by actual error types later
            content=exc.to_dict()
        )

    @app.exception_handler(Exception)
    async def universal_exception_handler(request: Request, exc: Exception):
        """Handle unexpected crashes gracefully."""
        logger.error(f"Unexpected crash for {request.url}: {exc}")
        return JSONResponse(
            status_code=500,
            content={"error": "InternalServerError", "message": "An unexpected error occurred."}
        )

    # 3. Router Registration
    from velocity.api.routes import agents, health, costs
    app.include_router(agents.router, prefix="/v1/agents", tags=["Agents"])
    app.include_router(costs.router, prefix="/v1/platform/costs", tags=["Costs"])
    app.include_router(health.router, tags=["Health"])

    @app.get("/")
    async def root():
        return {"platform": "Velocity", "version": "1.0.0", "status": "online"}

    return app

app = create_app()
