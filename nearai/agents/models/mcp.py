from pydantic import BaseModel
from typing import List, Dict, Optional
from enum import Enum

class MCPServerConfig(BaseModel):
    server_name: str
    url: Optional[str] = None
    command: Optional[str] = None
    args: Optional[List[str]] = None
    env: Dict[str, str] = {}

class MCPTransportType(str, Enum):
    SSE = "sse"
    STDIO = "stdio"
