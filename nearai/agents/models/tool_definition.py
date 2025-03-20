from typing import Dict, List, Literal
from pydantic import BaseModel, ConfigDict

class ToolParameterProperty(BaseModel):
    """Properties for a tool parameter."""
    type: str
    description: str
    enum: List[str] | None = None

    model_config = ConfigDict(
        extra='forbid',
        validate_assignment=True
    )

class ToolParameters(BaseModel):
    """Parameters configuration for a tool."""
    type: Literal["object"]
    properties: Dict[str, ToolParameterProperty]
    required: List[str]

    model_config = ConfigDict(
        extra='forbid',
        validate_assignment=True
    )

class ToolFunction(BaseModel):
    """Function definition for a tool."""
    name: str
    description: str
    parameters: ToolParameters

    model_config = ConfigDict(
        extra='forbid',
        validate_assignment=True
    )

class ToolDefinition(BaseModel):
    """Complete tool definition."""
    type: Literal["function"]
    function: ToolFunction

    model_config = ConfigDict(
        extra='forbid',
        validate_assignment=True
    )
