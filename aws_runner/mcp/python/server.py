from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client

from typing import Dict, Any, Optional, List, Callable
from pydantic import BaseModel
import inspect
import traceback
app = FastAPI()
mcp = FastMCP("dynamic-tools-server", port=4001)

class RegisterServerRequest(BaseModel):
    name: str
    command: Optional[str] = None
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    url: Optional[str] = None

@mcp.tool()
async def sum(a: int, b: int) -> int:
    print(f"Summing {a} and {b}")
    return a + b

async def create_tool_function(tool_name: str, input_schema: Dict[str, Any], transport_method: Callable, transport_params: Any):
    """Create a function with named parameters from the input schema"""
    # Extract parameter names and types from the schema
    params = {}
    for param_name, param_info in input_schema.get("properties", {}).items():
        param_type = param_info.get("type", "string")
        # Map JSON schema types to Python types
        type_mapping = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "array": List[Any],
            "object": Dict[str, Any]
        }
        params[param_name] = type_mapping.get(param_type, str)

    # Create the function signature
    async def tool_function(**kwargs):
        try:
            print(f"Creating tool function {tool_name} with arguments {kwargs}")
            async with transport_method(transport_params) as streams:
                async with ClientSession(streams[0], streams[1]) as session:
                    await session.initialize()
                    print(f"Calling tool {tool_name} with arguments {kwargs} and session {len((await session.list_tools()).tools)}")
                    return await session.call_tool(tool_name, kwargs)
        except Exception as e:
            print(f"Error calling tool {tool_name}: {traceback.format_exc()}")
            raise e

    # Set the function signature
    tool_function.__signature__ = inspect.Signature(
        parameters=[
            inspect.Parameter(
                name=param_name,
                kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                annotation=param_type
            )
            for param_name, param_type in params.items()
        ]
    )

    return tool_function

@mcp.tool()
async def register_server(settings: RegisterServerRequest) -> str:
    """Register a Python MCP server within the MCP server proxy"""
    try:
        print(f"Registering server {settings.name} with command {settings.command} and args {settings.args} and env {settings.env} and url {settings.url}")
        connection_methods = [
            {'name': 'stdio', 'present': (settings.command and settings.args) or
                                      (settings.command and settings.env) or
                                      settings.command},
            {'name': 'sse', 'present': bool(settings.url)}
        ]
        connection_methods = [m for m in connection_methods if m['present']]

        if len(connection_methods) != 1:
            raise ValueError("Exactly one connection method ('stdio' or 'sse') must be provided")

        connection_method = connection_methods[0]['name']
        transport_method = sse_client if connection_method == "sse" else stdio_client
        transport_params = (
            f"{settings.url}"
            if connection_method == "sse"
            else StdioServerParameters(
                command=settings.command or "",
                args=settings.args or [],
                env=settings.env or None,
            )
        )

        async with transport_method(transport_params) as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                print(f"Successfully connected to {settings.name}.")
                await session.initialize()

                print(f"Successfully initialized {settings.name}.")
                tools = (await session.list_tools()).tools

                for tool in tools:
                    print(f"Registering tool {tool.name} with schema {tool.inputSchema}")
                    # Create a tool function with named parameters
                    tool_function = await create_tool_function(tool.name, tool.inputSchema, transport_method, transport_params)
                    tool_function.__name__ = tool.name
                    tool_function.__doc__ = tool.description or ""

                    # Register the tool
                    mcp.add_tool(tool_function, tool.name, tool.description or "")

        return {
            "content": [{
                "type": "text",
                "text": f"MCP client {settings.name} registered successfully with {connection_method} connection"
            }]
        }
    except Exception as error:
        print(f"Error registering MCP client: {str(error)}")
        return {
            "content": [{
                "type": "text",
                "text": f"Error registering MCP client: {str(error)}"
            }],
            "isError": True
        }

# @app.get("/sse")
# async def sse_endpoint(request: Request):
#     async def event_generator():
#         while True:
#             if await request.is_disconnected():
#                 break
#             await asyncio.sleep(1)

#     return EventSourceResponse(event_generator())

# @app.post("/messages")
# async def messages_endpoint(request: Request):
#     data = await request.json()
#     await mcp.handle_message(data)
#     return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    print("Starting MCP server...")
    print(f"MCP Server running at http://localhost:4001")
    print(f"SSE endpoint available at http://localhost:4001/sse")
    print("Starting MCP server...")
    mcp.run(transport="sse")