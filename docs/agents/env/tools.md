# Tools & Commands

NEAR AI supports function based tool calling where the LLM can decide to call one of the functions (Tools) that you pass it.
You can register your own function or use any of the built-in tools (list_files, read_file, write_file, exec_command, query_vector_store, request_user_input).

The tool registry supports OpenAI style tool calling and Llama style. When a llama model is explicitly passed to completion(s)_and_run_tools
a system message is added to the conversation. This system message contains the tool definitions and instructions on how to invoke them 
using `<function>` tags.

To tell the LLM about your tools and automatically execute them when selected by the LLM, call one of these environment methods:

* [`completion_and_run_tools`](../../api.md#nearai.agents.environment.Environment.completion_and_run_tools): Allows tools to be passed and processes any returned tool_calls by running the tool
* [`completions_and_run_tools`](../../api.md#nearai.agents.environment.Environment.completions_and_run_tools): Handles tool calls and returns the full llm response.
* [`completion_and_get_tools_calls`](../../api.md#nearai.agents.environment.Environment.completion_and_get_tools_calls): Returns completion message and/or tool calls from OpenAI or Llama tool formats.

By default, these methods will add both the LLM response and tool invocation responses to the message list. 
You do not need to call `env.add_message` for these responses.
This behavior allows the LLM to see its call then tool responses in the message list on the next iteration or next run. 
This can be disabled by passing `add_to_messages=False` to the method.

## Registering Tools
* [`get_tool_registry`](../../api.md#nearai.agents.environment.Environment.get_tool_registry): returns the  tool registry, a dictionary of tools that can be called by the agent. By default
it is populated with the tools listed above for working with files and commands plus [`request_user_input`]
(../../api.md#nearai.agents.environment.Environment.request_user_input). To register a function as
a new tool, call [`register_tool`](../../api.md#nearai.agents.tool_registry.ToolRegistry.register_tool) on
the tool registry, passing it your function.

The tool registry provides two ways to register tools:

1. Using `register_tool` for regular Python functions/callables:
```python
def my_tool():
    """A simple tool that returns a string. This docstring helps the LLM know when to call the tool."""
    return "Hello from my tool"

tool_registry = env.get_tool_registry()
tool_registry.register_tool(my_tool)
tool_def = tool_registry.get_tool_definition('my_tool')
response = env.completions_and_run_tools(messages, tools=[tool_def])
```

2. Using `register_mcp_tool` for MCP tools:
```python
from nearai.agents.models.tool_definition import MCPTool

mcp_tool = MCPTool(
    name="weather",
    description="Get the current weather in a location",
    inputSchema={
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "The city and state, e.g. San Francisco, CA"
            }
        },
        "required": ["location"]
    }
)

async def call_weather_api(name: str, args: dict):
    # Implementation of the weather API call
    return f"Weather in {args['location']}: Sunny"

tool_registry.register_mcp_tool(mcp_tool, call_weather_api)
```

To pass all the built in tools plus any you have registered use the `get_all_tool_definitions` method.
```python
all_tools = env.get_tool_registry().get_all_tool_definitions()
response = env.completions_and_run_tools(messages, tools=all_tools)
```
If you do not want to use the built-in tools, use `get_tool_registry(new=True)`
```python
    tool_registry = env.get_tool_registry(new=True)
    tool_registry.register_tool(my_tool)
    tool_registry.register_tool(my_tool2)
    response = env.completions_and_run_tools(messages, tools=tool_registry.get_all_tool_definitions())
```

---

## Terminal Commands

Agents have access to the local terminal through the environment, the following methods are available:

| Method                                                                                            | Description                                                  |
|---------------------------------------------------------------------------------------------------|--------------------------------------------------------------|
| [`list_terminal_commands()`](../../api.md#nearai.agents.environment.Environment.list_terminal_commands) | Lists the history of terminal commands executed by the agent |
| [`exec_command(command)`](../../api.md#nearai.agents.environment.Environment.exec_command)              | Executes the terminal `command` and returns the output       |
