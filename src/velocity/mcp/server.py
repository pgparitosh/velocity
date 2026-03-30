"""
MCP Server.
Exposes platform-native tools via the Model Context Protocol (MCP).
Allows external LLM clients to consume Velocity tools securely.
"""

from fastapi import FastAPI, Request
from typing import Any, Dict

from velocity.tools.registry import ToolRegistry

app = FastAPI(title="Velocity MCP Server")
registry = ToolRegistry()

@app.post("/")
async def mcp_endpoint(request: Request) -> Dict[str, Any]:
    """
    Main JSON-RPC 2.0 entry point for the MCP protocol.
    """
    data = await request.json()
    method = data.get("method")
    params = data.get("params", {})
    request_id = data.get("id")

    if method == "tools/list":
        # Export all tools. 
        # In production, this would be gated by the API key / Token permissions.
        tools = registry.get_agent_schemas(active_permissions=["*"])
        return {
            "jsonrpc": "2.0",
            "result": {"tools": tools},
            "id": request_id
        }

    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        # Implementation Note: 
        # Executing a Velocity tool requires an AgentContext (for cost, audit, tracing).
        # An MCP-only client might not provide this. 
        # A production implementation would derive context from the authenticated request.
        
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32601,
                "message": f"Method 'tools/call' for '{tool_name}' is accepted but requires AgentContext bindings not present in this standalone MCP shim."
            },
            "id": request_id
        }

    return {
        "jsonrpc": "2.0",
        "error": {"code": -32601, "message": "Method not found"},
        "id": request_id
    }
