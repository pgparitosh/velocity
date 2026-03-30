__version__ = "1.0.0"

# Expose main exceptions at the root for convenience
from .exceptions import (
    BudgetExceededError,
    InputValidationError,
    LLMUnavailableError,
    PromptNotFoundError,
    RateLimitExceededError,
    SecurityValidationError,
    ToolInputValidationError,
    ToolNotFoundError,
    ToolPermissionError,
    ToolSecurityError,
    ToolTimeoutError,
    VelocityError,
    WorkflowRejectedError,
    WorkflowTimeoutError,
)

__all__ = [
    "__version__",
    "VelocityError",
    "BudgetExceededError",
    "RateLimitExceededError",
    "LLMUnavailableError",
    "ToolNotFoundError",
    "ToolPermissionError",
    "ToolTimeoutError",
    "ToolInputValidationError",
    "SecurityValidationError",
    "ToolSecurityError",
    "PromptNotFoundError",
    "InputValidationError",
    "WorkflowRejectedError",
    "WorkflowTimeoutError",
]
