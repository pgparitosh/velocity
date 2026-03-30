"""
Velocity platform exception hierarchy.
All platform-specific exceptions should inherit from `VelocityError`.
"""

from typing import Any


class VelocityError(Exception):
    """
    Base exception for all Velocity platform errors.
    
    Provides structured error context (request_id, agent_id, details)
    to facilitate easy serialization into API responses (e.g., JSON).
    """

    def __init__(
        self,
        message: str,
        request_id: str | None = None,
        agent_id: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.request_id = request_id
        self.agent_id = agent_id
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """Serialize error for API responses."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "request_id": self.request_id,
            "agent_id": self.agent_id,
            "details": self.details,
        }


# -----------------------------------------------------------------------------
# Core Engine Errors
# -----------------------------------------------------------------------------

class BudgetExceededError(VelocityError):
    """Raised when an agent invocation exceeds the platform or tenant budget."""
    pass


class RateLimitExceededError(VelocityError):
    """Raised when tenant or platform-wide rate limits are surpassed."""
    pass


class LLMUnavailableError(VelocityError):
    """Raised when the LLM gateway exhausts all retries and fallback options."""
    pass


# -----------------------------------------------------------------------------
# Tool Layer Errors
# -----------------------------------------------------------------------------

class ToolNotFoundError(VelocityError):
    """Raised when an agent attempts to execute an unregistered tool."""
    pass


class ToolPermissionError(VelocityError):
    """Raised when an agent attempts to invoke a tool it lacks RBAC permissions for."""
    pass


class ToolTimeoutError(VelocityError):
    """Raised when a tool execution exceeds its configured timeout bounding."""
    pass


class ToolInputValidationError(VelocityError):
    """Raised when an LLM provides invalid arguments failing the tool's JSON schema."""
    pass


# -----------------------------------------------------------------------------
# Knowledge Layer Errors
# -----------------------------------------------------------------------------

class PromptNotFoundError(VelocityError):
    """Raised when a specified prompt reference cannot be resolved."""
    pass


# -----------------------------------------------------------------------------
# Safety & Compliance Errors
# -----------------------------------------------------------------------------

class SecurityValidationError(VelocityError):
    """Raised during pre-flight or post-flight security checks (e.g., PII detected)."""
    pass


class ToolSecurityError(VelocityError):
    """Raised when a tool output fails security sanitization."""
    pass


class InputValidationError(VelocityError):
    """Raised when initial user payload fails the agent's input JSON schema."""
    pass


# -----------------------------------------------------------------------------
# Orchestration Errors
# -----------------------------------------------------------------------------

class WorkflowRejectedError(VelocityError):
    """Raised when a multi-agent workflow is explicitly rejected by a condition or human gate."""
    pass


class WorkflowTimeoutError(VelocityError):
    """Raised when a multi-agent workflow stalls and exceeds total allowed elapsed time."""
    pass
