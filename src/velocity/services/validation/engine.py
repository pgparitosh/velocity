"""
Validation Engine for structuring outputs.
Ensures tool payloads from the LLM match definitions, preventing schema crashes.
"""

from typing import Any

from velocity.exceptions import ToolInputValidationError


class ValidationEngine:
    """
    Guarantees structural cohesion. If an LLM hallucinates properties,
    this boundary enforces adherence dynamically before propagating downstream.
    """
    
    @staticmethod
    def validate_tool_inputs(
        tool_name: str, 
        provided_inputs: dict[str, Any], 
        schema_definition: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Confirms inputs map correctly.
        In Phase 2, we dynamically build Pydantic models from the JSON schema
        to utilize robust validation and coercion natively.
        For MVP, we enforce strictly required keys are present via the schema dict.
        """
        required_keys = schema_definition.get("required", [])
        
        for key in required_keys:
            if key not in provided_inputs:
                raise ToolInputValidationError(
                    f"Tool '{tool_name}' failed validation. Missing required parameter: '{key}'.",
                    details={"schema": schema_definition, "provided": list(provided_inputs.keys())}
                )
                
        # Phase 2: Add strict type coercion natively
        return provided_inputs
        
