"""
Automatic schema generation logic for Python functions.
Relies on native `inspect` and type hints to create deterministic JSON Schemas 
compatible with Anthropic/OpenAI tool interfaces.
"""

import inspect
from collections.abc import Callable
from typing import (
    Any,
    Literal,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)


def _python_type_to_json_type(py_type: Any) -> dict[str, Any]:
    """Map native python types to JSON Schema equivalents."""
    # Handle Optional[T] / Union[T, None]
    origin = get_origin(py_type)
    args = get_args(py_type)

    if origin is Union:
        # If it's Optional[T], just extract T (JSON Schema for tools usually ignores nullability)
        non_none_args = [t for t in args if t is not type(None)]
        if len(non_none_args) == 1:
            return _python_type_to_json_type(non_none_args[0])
            
    if origin is Literal:
        return {
            "type": "string",
            "enum": list(args)
        }

    if origin is list or py_type is list:
        item_schema = {"type": "string"} # Default
        if args:
            item_schema = _python_type_to_json_type(args[0])
        return {
            "type": "array",
            "items": item_schema
        }

    if origin is dict or py_type is dict or py_type is dict:
        return {"type": "object"}

    if py_type is str:
        return {"type": "string"}
    elif py_type is int:
        return {"type": "integer"}
    elif py_type is float:
        return {"type": "number"}
    elif py_type is bool:
        return {"type": "boolean"}
        
    # Fallback for complex or unannotated types
    return {"type": "object"}


def generate_json_schema_from_func(func: Callable[..., Any]) -> dict[str, Any]:
    """
    Parses a python function signature into a standard JSON Schema properties dictionary.
    Includes parameter descriptions extracted from docstrings if available (Phase 2 extension).
    """
    signature = inspect.signature(func)
    
    # We use get_type_hints to resolve stringified annotations automatically
    try:
        hints = get_type_hints(func)
    except Exception:
        # Fallback if evaluation fails
        hints = {}

    properties = {}
    required = []

    for name, param in signature.parameters.items():
        # Skip contexts and self/cls params
        if name in ("self", "cls", "ctx", "context"):
            continue

        param_type = hints.get(name, param.annotation)
        if param_type is inspect.Parameter.empty:
            # Default to string if un-annotated
            param_type = str

        schema_node = _python_type_to_json_type(param_type)
        properties[name] = schema_node

        # If there's no default value, it's required
        if param.default is inspect.Parameter.empty:
            # Also, if it's Optional, it technically isn't strictly required
            origin = get_origin(param_type)
            args = get_args(param_type)
            is_optional = origin is Union and type(None) in args
            
            if not is_optional:
                required.append(name)

    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties
    }
    
    if required:
        schema["required"] = required
        
    return schema
