
import pytest

from velocity.core.context import AgentContext
from velocity.exceptions import ToolNotFoundError, ToolPermissionError
from velocity.tools.decorators import tool
from velocity.tools.registry import ToolRegistry


@tool(name="search", description="Search tool")
async def search_tool(query: str):
    return f"Results for {query}"

@tool(name="delete", description="Delete tool", requires_permissions=["admin"])
async def delete_tool(item_id: str):
    return f"Deleted {item_id}"

def test_tool_registry_registration():
    registry = ToolRegistry()
    registry.register(search_tool)
    
    # ToolRegistry stores in self._registry
    assert "search" in registry._registry
    metadata = registry.get_metadata("search")
    assert metadata.name == "search"
    assert metadata.description == "Search tool"

@pytest.mark.asyncio
async def test_tool_registry_execution():
    registry = ToolRegistry()
    registry.register(search_tool)
    
    ctx = AgentContext(request_id="r1", agent_id="a1", tenant_id="t1")
    # ToolRegistry.execute(name, inputs, ctx, agent_permissions)
    result = await registry.execute("search", {"query": "test"}, ctx, agent_permissions=[])
    assert result == "Results for test"

@pytest.mark.asyncio
async def test_tool_registry_rbac_allowed():
    registry = ToolRegistry()
    registry.register(delete_tool)
    
    ctx = AgentContext(request_id="r1", agent_id="a1", tenant_id="t1")
    # Should not raise
    await registry.execute("delete", {"item_id": "123"}, ctx, agent_permissions=["admin"])

@pytest.mark.asyncio
async def test_tool_registry_rbac_denied():
    registry = ToolRegistry()
    registry.register(delete_tool)
    
    ctx = AgentContext(request_id="r1", agent_id="a1", tenant_id="t1")
    with pytest.raises(ToolPermissionError):
        await registry.execute("delete", {"item_id": "123"}, ctx, agent_permissions=["user"])

def test_tool_registry_not_found():
    registry = ToolRegistry()
    with pytest.raises(ToolNotFoundError):
        registry.get_metadata("non-existent")
