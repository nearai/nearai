from typing import Optional, Dict, Callable


class ToolRegistry:
    def __init__(self):
        self.tools = {}

    def register_tool(self, tool: Callable):
        self.tools[tool.__name__] = tool

    def get_tool(self, name) -> Optional[Callable]:
        return self.tools.get(name)

    def get_all_tools(self) -> Dict[str, Callable]:
        return self.tools.values()

    def call_tool(self, name, **kwargs):
        tool = self.get_tool(name)
        if tool is None:
            raise ValueError(f"Tool '{name}' not found.")
        return tool(**kwargs)