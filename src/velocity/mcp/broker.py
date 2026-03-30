"""
MCP Broker.
Orchestrates connections to Model Context Protocol (MCP) servers.
Translates external tool definitions into platform-native metadata.
"""

import logging
import httpx
from typing import Any, Dict, List

from velocity.tools.metadata import ToolMetadata

logger = logging.getLogger(__name__)


class MCPBroker:
    """
    Connects the Velocity platform to external Model Context Protocol (MCP) servers.
    Handles tool discovery and routing.
    """

    def __init__(self, server_configs: List[Dict[str, Any]]):
        """
        Initialize the broker with a list of MCP server configurations.
        
        server_configs example:
        [
            {"name": "internal-tools", "url": "http://mcp-server-1:8080"},
            {"name": "external-docs", "url": "http://mcp-server-2:8080"}
        ]
        """
        self.server_configs = server_configs
        self.clients: Dict[str, httpx.AsyncClient] = {
            config["name"]: httpx.AsyncClient(base_url=config["url"])
            for config in server_configs
        }
        self._tool_to_server_map: Dict[str, str] = {}

    async def discover_tools(self) -> List[ToolMetadata]:
        """
        Query all configured MCP servers for their available tools.
        Returns a list of ToolMetadata objects (virtual tools).
        """
        all_metadata = []
        for name, client in self.clients.items():
            try:
                # MCP tools/list pattern
                response = await client.post("/", json={
                    "jsonrpc": "2.0",
                    "method": "tools/list",
                    "params": {},
                    "id": 1
                })
                response.raise_for_status()
                data = response.json()
                
                tools = data.get("result", {}).get("tools", [])
                for tool_def in tools:
                    tool_name = tool_def["name"]
                    # Map the tool to this server for later execution
                    self._tool_to_server_map[tool_name] = name
                    
                    # Convert MCP tool def to Velocity ToolMetadata
                    # We create a proxy handler that calls the MCP server
                    metadata = ToolMetadata(
                        name=tool_name,
                        description=tool_def.get("description", ""),
                        handler=self._create_mcp_handler(name, tool_name),
                        input_schema=tool_def.get("input_schema", {}),
                        requires_permissions=[] # MCP tools might handle their own auth
                    )
                    all_metadata.append(metadata)
                    
            except Exception as e:
                logger.error(f"Failed to discover tools from MCP server '{name}': {e}")
                
        return all_metadata

    def _create_mcp_handler(self, server_name: str, tool_name: str) -> Any:
        """Create a closure that routes tool execution to the MCP server."""
        async def mcp_handler(**kwargs: Any) -> Any:
            client = self.clients[server_name]
            response = await client.post("/", json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": kwargs
                },
                "id": 1
            })
            response.raise_for_status()
            res_data = response.json()
            
            if "error" in res_data:
                raise Exception(f"MCP Tool Error [{tool_name}]: {res_data['error']}")
                
            return res_data.get("result", {}).get("content", [])
            
        return mcp_handler

    async def close(self) -> None:
        """Shutdown all clients."""
        for client in self.clients.values():
            await client.aclose()
