from typing import Any
from pydantic import BaseModel, ConfigDict

class MCPTool(BaseModel):
    """Definition for a tool the client can call."""

    name: str
    """The name of the tool."""
    description: str | None = None
    """A human-readable description of the tool."""
    inputSchema: dict[str, Any]
    """A JSON Schema object defining the expected parameters for the tool."""
    model_config = ConfigDict(extra="allow")