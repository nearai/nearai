import inspect
from typing import Any, Callable, Dict, Literal, Optional, _GenericAlias, get_type_hints  # type: ignore

from nearai.agents.models.tool_definition import MCPTool


class ToolRegistry:
    """A registry for tools that can be called by the agent.

    Tool definitions follow this structure:

        {
            "type": "function",
            "function": {
                "name": "get_current_weather",
                "description": "Get the current weather in a given location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city and state, e.g. San Francisco, CA",
                        },
                        "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                    },
                    "required": ["location"],
                },
            },
        }

    """

    def __init__(self) -> None:  # noqa: D107
        self.tools: Dict[str, Callable] = {}

    def register_tool(self, tool: Callable) -> None:  # noqa: D102
        """Register a tool."""
        self.tools[tool.__name__] = tool

    def register_mcp_tool(self, mcp_tool: MCPTool, call_tool: Callable) -> None:  # noqa: D102
        """Register a tool callable from its definition."""

        async def tool(**kwargs):
            try:
                return await call_tool(mcp_tool.name, kwargs)
            except Exception as e:
                raise Exception(f"Error calling tool {mcp_tool.name} with arguments {kwargs}: {e}") from e

        tool.__name__ = mcp_tool.name
        tool.__doc__ = mcp_tool.description
        tool.__setattr__("__schema__", mcp_tool.inputSchema)

        self.tools[mcp_tool.name] = tool

    def get_tool(self, name: str) -> Optional[Callable]:  # noqa: D102
        """Get a tool by name."""
        return self.tools.get(name)

    def get_all_tools(self) -> Dict[str, Callable]:  # noqa: D102
        """Get all tools."""
        return self.tools

    def call_tool(self, name: str, **kwargs: Any) -> Any:  # noqa: D102
        """Call a tool by name."""
        tool = self.get_tool(name)
        if tool is None:
            raise ValueError(f"Tool '{name}' not found.")
        return tool(**kwargs)

    def get_tool_definition(self, name: str) -> Optional[Dict]:  # noqa: D102
        """Get the definition of a tool by name."""
        tool = self.get_tool(name)
        if tool is None:
            return None

        assert tool.__doc__ is not None, f"Docstring missing for tool '{name}'."
        docstring = tool.__doc__.strip().split("\n")

        # The first line of the docstring is the function description
        function_description = docstring[0].strip()

        # The rest of the lines contain parameter descriptions
        param_descriptions = docstring[1:]

        # Extract parameter names and types
        signature = inspect.signature(tool)
        type_hints = get_type_hints(tool)

        parameters: Dict[str, Any] = {"type": "object", "properties": {}, "required": []}

        if hasattr(tool, "__schema__"):
            return {
                "type": "function",
                "function": {"name": tool.__name__, "description": function_description, "parameters": tool.__schema__},
            }

        # Iterate through function parameters
        for param in signature.parameters.values():
            param_name = param.name
            param_type = type_hints.get(param_name, str)  # Default to str if type hint is missing
            param_description = ""

            # Find the parameter description in the docstring
            for line in param_descriptions:
                if line.strip().startswith(param_name):
                    param_description = line.strip().split(":", 1)[1].strip()
                    break

            # Convert type hint to JSON Schema type
            if isinstance(param_type, _GenericAlias) and param_type.__origin__ is Literal:
                json_type = "string"
            else:
                json_type = param_type.__name__.lower()

            if json_type == "union":
                json_type = [t.__name__.lower() for t in param_type.__args__][0]

            json_type = {"int": "integer", "float": "number", "str": "string", "bool": "boolean"}.get(
                json_type, "string"
            )

            # Add parameter to the definition
            parameters["properties"][param_name] = {"description": param_description, "type": json_type}

            # Params without default values are required params
            if param.default == inspect.Parameter.empty:
                parameters["required"].append(param_name)

        return {
            "type": "function",
            "function": {"name": tool.__name__, "description": function_description, "parameters": parameters},
        }

    def get_all_tool_definitions(self) -> list[Dict]:  # noqa: D102
        definitions = []
        for tool_name, _tool in self.tools.items():
            definition = self.get_tool_definition(tool_name)
            if definition is not None:
                definitions.append(definition)
        return definitions
