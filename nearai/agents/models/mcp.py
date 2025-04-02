from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel


class MCPServerConfig(BaseModel):
    server_name: str
    url: Optional[str] = None
    command: Optional[str] = None
    args: Optional[List[str]] = None
    env: Dict[str, str] = {}


class MCPTransportType(str, Enum):
    SSE = "sse"
    STDIO = "stdio"
