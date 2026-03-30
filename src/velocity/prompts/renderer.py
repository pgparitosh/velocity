"""
Prompt Variable Substitution Engine.
Safely replaces {variable} placeholders in prompt templates with actual runtime values.
"""

from typing import Any

from velocity.exceptions import VelocityError


class PromptCompilationError(VelocityError):
    """Raised when variable substitution fails during prompt rendering."""
    pass


def render_prompt(template: str, variables: dict[str, Any]) -> str:
    """
    Renders a template string by substituting named placeholders securely.
    
    Args:
        template: The raw text template (e.g., 'Hello, {name}.')
        variables: The runtime context variables supplied to the agent.
        
    Returns:
        The fully resolved text prompt suitable for the LLM. 
        
    Raises:
        PromptCompilationError if a required variable is missing or mismatched.
    """
    try:
        # We use standard format() for high performance string interpolation.
        # Strict mode: missing variables will raise KeyError naturally here.
        return template.format(**variables)
    except KeyError as e:
        missing_key = str(e).strip("'")
        raise PromptCompilationError(
            f"Failed to render prompt. Missing required variable: '{missing_key}'",
            details={"missing_key": missing_key, "provided_variables": list(variables.keys())}
        ) from e
    except Exception as e:
        raise PromptCompilationError(
            f"Unexpected error compiling prompt: {str(e)}",
            details={"error_type": type(e).__name__}
        ) from e
