from typing import Any, Literal

from velocity.tools.schema_gen import generate_json_schema_from_func


def test_generate_schema_basic():
    def simple_func(name: str, age: int):
        pass
    
    schema = generate_json_schema_from_func(simple_func)
    assert schema["type"] == "object"
    assert "name" in schema["properties"]
    assert schema["properties"]["name"]["type"] == "string"
    assert schema["properties"]["age"]["type"] == "integer"
    assert "name" in schema["required"]
    assert "age" in schema["required"]

def test_generate_schema_defaults_and_optionals():
    def func_with_defaults(name: str, tags: list[str] = None):
        pass
    
    schema = generate_json_schema_from_func(func_with_defaults)
    # In our current impl, if default is None, it's not in required
    assert "name" in schema["required"]
    assert "tags" not in schema.get("required", [])

def test_generate_schema_complex_types():
    def complex_func(
        scores: list[float],
        status: Literal["active", "inactive"] = "active"
    ):
        pass
    
    schema = generate_json_schema_from_func(complex_func)
    assert schema["properties"]["scores"]["type"] == "array"
    assert schema["properties"]["scores"]["items"]["type"] == "number"
    assert schema["properties"]["status"]["type"] == "string"
    assert schema["properties"]["status"]["enum"] == ["active", "inactive"]

def test_generate_schema_skipping_internal_params():
    def tool_func(ctx: Any, name: str):
        pass
    
    schema = generate_json_schema_from_func(tool_func)
    # ctx should be skipped
    assert "ctx" not in schema["properties"]
    assert "name" in schema["properties"]
