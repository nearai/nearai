from typing import Any

from pydantic import BaseModel, ConfigDict


# TODO: We should import the mcp Tool types from the MCP package
# This is temporary since we have some dependencies conflicting with the MCP package
class MCPTool(BaseModel):
    """Definition for a tool the client can call."""

    name: str
    """The name of the tool."""
    description: str = ""
    """A human-readable description of the tool."""
    inputSchema: dict[str, Any]  # noqa: N815
    """A JSON Schema object defining the expected parameters for the tool."""
    model_config = ConfigDict(extra="allow")
