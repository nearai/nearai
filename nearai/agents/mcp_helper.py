"""Helper module for MCP (Model Control Protocol) server functionality."""

import asyncio
import json
import logging
from dataclasses import dataclass
import traceback
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Protocol

from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.stdio import StdioServerParameters, stdio_client
from openai.types.beta.threads.message import Message

from nearai.agents.models.mcp import MCPServerConfig, MCPTransportType
from nearai.agents.tool_registry import ToolRegistry

INITIALIZATION_TIMEOUT = 30  # seconds
TOOL_EXECUTION_TIMEOUT = 60  # seconds

class MCPError(Exception):
    """Base exception for MCP-related errors."""


class MCPConnectionError(MCPError):
    """Raised when there's an error connecting to an MCP server."""


class MCPToolError(MCPError):
    """Raised when there's an error with MCP tools."""


class MCPStateError(MCPError):
    """Raised when there's an error with MCP state management."""


class Logger(Protocol):
    """Protocol for logging interface."""

    def __call__(self, message: str, level: int = logging.INFO) -> None: ...


@dataclass
class MCPToolData:
    """Data structure for MCP tool information."""

    tool: Dict[str, Any]
    server_name: str


@dataclass
class MCPServerData:
    """Data structure for MCP server information."""

    name: str
    tools: List[MCPToolData]
    server_map: Dict[str, Any]

class MCPServerManager:
    """Manages MCP servers and their tools."""

    def __init__(
        self,
        logger: Logger,
        add_reply: Callable[[str], None],
        save_agent_data: Callable[[str, Any], None],
        get_agent_data: Callable[[str], Optional[Dict]],
        get_messages: Callable[[], List[Dict]],
        get_tool_completion: Callable[[List[Dict], List[Dict]], Any],
    ):
        """Initialize the MCP server manager.

        Args:
            logger: Function to log messages
            add_reply: Function to add replies to conversation
            save_agent_data: Function to save agent data
            get_agent_data: Function to get agent data
            get_messages: Function to get conversation messages
            get_tool_completion: Function to get tool completion
        """
        self.logger = logger
        self.add_reply = add_reply
        self.save_agent_data = save_agent_data
        self.get_agent_data = get_agent_data
        self.get_messages = get_messages
        self.get_tool_completion = get_tool_completion

    def validate_state(self, state: Dict) -> bool:
        """Validate that the MCP state contains all required fields.

        Args:
            state: The MCP state dictionary to validate

        Returns:
            True if state is valid, False otherwise
        """
        return bool(
            state
            and isinstance(state, dict)
            and all(k in state for k in ["servers", "tools", "configs"])
        )

    def get_server_names(self, configs: List[MCPServerConfig]) -> Set[str]:
        """Extract server names from MCP server configs.

        Args:
            configs: List of MCP server configurations

        Returns:
            Set of server names
        """
        return {
            config.name if isinstance(config, MCPServerConfig) else config["name"]
            for config in configs
        }

    async def get_transport_method(
        self,
        mcp_server_config: MCPServerConfig
    ) -> Tuple[Callable, Any]:
        """Get the transport method and parameters for an MCP server config.

        Args:
            mcp_server_config: The server configuration

        Returns:
            Tuple containing the transport method and parameters

        Raises:
            MCPConnectionError: If server configuration is invalid
        """
        self.logger(f"MCP SERVER CONFIG: {mcp_server_config}")

        # Convert dict to MCPServerConfig if needed
        if isinstance(mcp_server_config, dict):
            mcp_server_config = MCPServerConfig(**mcp_server_config)

        if mcp_server_config.url is None and mcp_server_config.command is None:
            raise MCPConnectionError("MCP server needs either a url or a command to be set")

        transport_type = MCPTransportType.SSE if mcp_server_config.url else MCPTransportType.STDIO
        self.logger(f"Connecting to MCP Server {mcp_server_config.name} using {transport_type}...")

        transport_method = sse_client if transport_type == MCPTransportType.SSE else stdio_client

        transport_params = (
            f"{mcp_server_config.url}"
            if transport_type == MCPTransportType.SSE
            else StdioServerParameters(
                command=mcp_server_config.command or "",
                args=mcp_server_config.args or [],
                env=mcp_server_config.env or None,
            )
        )
        return transport_method, transport_params

    async def initialize_server(
        self,
        transport_method: Callable,
        transport_params: Any,
        server_name: str,
    ) -> Tuple[ClientSession, List[Any]]:
        """Initialize an MCP server and get available tools.

        Args:
            transport_method: The transport method to use
            transport_params: Parameters for the transport method
            server_name: Name of the server being initialized

        Returns:
            Tuple containing the initialized session and list of available tools

        Raises:
            MCPConnectionError: If server initialization fails
        """
        try:
            async with transport_method(transport_params) as streams:
                async with ClientSession(streams[0], streams[1]) as session:
                  self.logger(f"Successfully connected to {server_name}.")
                  await session.initialize()

                  self.logger(f"Successfully initialized {server_name}.")
                  tools = (await asyncio.wait_for(
                      session.list_tools(),
                      timeout=INITIALIZATION_TIMEOUT
                  )).tools
                  self.logger(f"Found {len(tools)} tools")
                  return session, tools
        except Exception as e:
            raise MCPConnectionError(f"Failed to initialize server {server_name}: {traceback.format_exc()}") from e

    async def register_tool(
        self,
        mcp_tool: Any,
        server_name: str,
        server_config: MCPServerConfig,
        tool_registry: ToolRegistry,
    ) -> MCPToolData:
        """Register a single MCP tool and prepare its server map entry.

        Args:
            mcp_tool: The tool to register
            server_name: Name of the server providing the tool
            transport_method: The transport method to use
            transport_params: Parameters for the transport method
            tool_registry: Registry to add the tool to

        Returns:
            MCPToolData containing the registered tool information

        Raises:
            MCPToolError: If tool registration fails
        """
        try:
            tool_registry.register_mcp_tool(mcp_tool.model_dump(), None)  # Call_tool will be set during execution

            server_map_entry = {
                "name": server_name,
                "config": server_config
            }

            tool_data = MCPToolData(
                tool=mcp_tool.model_dump(),
                server_name=server_name
            )

            self.logger(f"Registered tool {mcp_tool.name} from server {server_name}")
            return tool_data, {mcp_tool.name: server_map_entry}
        except Exception as e:
            raise MCPToolError(f"Failed to register tool {mcp_tool.name}: {traceback.format_exc()}") from e

    async def add_server(
        self,
        mcp_server_config: MCPServerConfig,
        tool_registry: ToolRegistry,
    ) -> MCPServerData:
        """Add a single MCP server and register its tools.

        Args:
            mcp_server_config: The server configuration to add
            tool_registry: The tool registry to register tools with

        Returns:
            MCPServerData containing server information and registered tools

        Raises:
            MCPError: If server addition fails
        """
        if isinstance(mcp_server_config, dict):
            mcp_server_config = MCPServerConfig(**mcp_server_config)

        try:
            transport_method, transport_params = await self.get_transport_method(mcp_server_config)
            server_name = mcp_server_config.name

            session, mcp_tools = await self.initialize_server(
                transport_method, transport_params, server_name
            )

            tools_data = []
            server_tool_map = {}

            for mcp_tool in mcp_tools:
                tool_data, map_entry = await self.register_tool(
                    mcp_tool,
                    server_name,
                    mcp_server_config,
                    tool_registry,
                )
                tools_data.append(tool_data)
                server_tool_map.update(map_entry)

            return MCPServerData(
                name=server_name,
                tools=tools_data,
                server_map=server_tool_map
            )

        except Exception as e:
            self.logger(
                f"Error adding MCP Server ({mcp_server_config.name}): {traceback.format_exc()}",
                logging.ERROR
            )
            raise MCPError(f"Failed to add server {mcp_server_config.name}: {e}") from e

    async def execute_tool(
        self,
        tool_call: Any,
        server: Dict[str, Any],
    ) -> Optional[Any]:
        """Execute a single tool call.

        Args:
            tool_call: The tool call to execute
            server: Server information for the tool

        Returns:
            Tool execution result or None if execution failed

        Raises:
            MCPToolError: If tool execution fails
        """
        try:
            self.logger(f"Connecting to {server['name']} to execute {tool_call.function.name}...")
            server_config = server["config"]
            transport_method, transport_params = await self.get_transport_method(server_config)

            async with transport_method(transport_params) as streams:
                async with ClientSession(streams[0], streams[1]) as session:
                  self.logger(f"Successfully connected to {server['name']}.")
                  try:
                    await session.initialize()
                    self.logger(f"Successfully initialized {server['name']}.")
                    tool_result = await asyncio.wait_for(
                        session.call_tool(
                            tool_call.function.name,
                            json.loads(tool_call.function.arguments)
                        ),
                        timeout=TOOL_EXECUTION_TIMEOUT
                    )
                    self.logger(f"Tool result inside: {tool_result}")
                    return tool_result
                  except asyncio.TimeoutError:
                    self.logger(f"Tool execution timed out after 1 minute")
                    return {"error": "Tool execution timed out after 1 minute"}

        except Exception as e:
            raise MCPToolError(f"Failed to execute tool {tool_call.function.name}: {traceback.format_exc()}") from e

    async def process_tool_result(
        self,
        tool_result: Any,
        add_responses_to_messages: bool,
    ) -> Optional[str]:
        """Process the result from a tool execution.

        Args:
            tool_result: Result from tool execution
            add_responses_to_messages: Whether to add responses to messages

        Returns:
            Optional tool response string
        """
        if not tool_result or not hasattr(tool_result, "content"):
            if add_responses_to_messages:
                self.add_reply("No content received from tool")
            return None

        for content in tool_result.content:
            try:
                result_json = json.loads(content.text)
                formatted_result = json.dumps(result_json, indent=2)
                if add_responses_to_messages:
                    self.add_reply(formatted_result)
                else:
                    return formatted_result
            except json.JSONDecodeError:
                if add_responses_to_messages:
                    self.add_reply(content.text)
                else:
                    return content.text
        return None

    async def handle_tool_calls(
        self,
        completion: Message,
        tool_server_map: Dict[str, Any],
        add_responses_to_messages: bool = True,
    ) -> Optional[str]:
        """Handle MCP tool calls from a completion.

        Args:
            completion: The completion message containing tool calls
            tool_server_map: Mapping of tool names to server info
            add_responses_to_messages: Whether to add tool responses to messages

        Returns:
            Optional tool response string

        Raises:
            MCPToolError: If tool execution fails
        """
        for tool_call in completion.tool_calls:
            server = tool_server_map.get(tool_call.function.name)
            if not server:
                self.logger(f"Tool {tool_call.function.name} not found in tool_server_map", logging.ERROR)
                continue

            try:
                tool_result = await self.execute_tool(tool_call, server)
                self.logger(f"Tool result: {tool_result}")
                if tool_result:
                    result = await self.process_tool_result(
                        tool_result,
                        add_responses_to_messages
                    )
                    if result:
                        return result
            except MCPToolError as e:
                self.logger(f"Error executing tool: {e}", logging.ERROR)
                if add_responses_to_messages:
                    self.add_reply(f"Error executing tool: {e}")

        return None

    async def restore_saved_state(
        self,
        state: Dict[str, Any],
        tool_registry: ToolRegistry,
    ) -> Dict[str, Any]:
        """Restore MCP state from saved configuration.

        Args:
            state: The saved state to restore
            tool_registry: The tool registry to use

        Returns:
            Tool server map for restored tools

        Raises:
            MCPError: If state restoration fails
        """
        self.logger("Found matching saved MCP state, loading tools and servers...")
        tool_server_map = {}

        try:
            # Reconstruct tools and server map
            for tool_data in state["tools"]:
                mcp_tool = tool_data["tool"]
                server_name = tool_data["server_name"]
                server_config = next(
                    (conf for conf in state["configs"] if (isinstance(conf, dict) and conf.get("name") == server_name)),
                    None
                )

                if server_config:
                    tool_registry.register_mcp_tool(mcp_tool, None)
                    tool_server_map[mcp_tool['name']] = {
                        "name": server_name,
                        "config": server_config
                    }

            self.add_reply(f"Loaded {len(state['servers'])} MCP servers and {len(tool_server_map)} MCP tools from saved state")
            return tool_server_map

        except Exception as e:
            raise MCPStateError(f"Failed to restore saved state: {e}") from e

    async def process_new_servers(
        self,
        configs: List[MCPServerConfig],
        tool_registry: ToolRegistry,
    ) -> Dict[str, Any]:
        """Process and add new MCP server configurations.

        Args:
            configs: List of server configurations to process
            tool_registry: The tool registry to use

        Returns:
            Tool server map for added servers

        Raises:
            MCPError: If server processing fails
        """
        self.logger("Processing new server configurations...")
        servers_data = []
        tool_server_map = {}

        try:
            for config in configs:
                server_data = await self.add_server(config, tool_registry)
                servers_data.append(server_data)
                tool_server_map.update(server_data.server_map)

            mcp_state = {
                "servers": [server.name for server in servers_data],
                "tools": [
                    {"tool": tool.tool, "server_name": tool.server_name}
                    for server in servers_data
                    for tool in server.tools
                ],
                "configs": [
                    config.model_dump() if isinstance(config, MCPServerConfig) else config
                    for config in configs
                ]
            }
            self.save_agent_data("mcp_state", mcp_state)
            self.add_reply("Saved complete MCP state for future use")

            return tool_server_map

        except Exception as e:
            raise MCPError(f"Failed to process new servers: {e}") from e

    async def run_tool_completion(
        self,
        tool_registry: ToolRegistry,
        tool_server_map: Dict[str, Any],
        add_responses_to_messages: bool = True,
    ) -> None:
        """Run tool completion with the configured tools.

        Args:
            tool_registry: The tool registry containing available tools
            tool_server_map: Mapping of tools to their servers
            add_responses_to_messages: Whether to add responses to messages

        Raises:
            MCPError: If tool completion fails
        """
        try:
            self.logger(f"{len(tool_registry.get_all_tool_definitions())} tools registered!")
            self.logger(f"TOOL REGISTRY: {tool_registry.get_all_tool_definitions()}")

            completion = self.get_tool_completion(
                [
                    {
                        "role": "system",
                        "content": "You are an assistant and you can use a list of tools to help answer user questions. I want all your response to be human friendly formatted. So if you receive a JSON object, you should format it as a human readable string.",
                    }
                ] + self.get_messages(),
                tools=tool_registry.get_all_tool_definitions(),
            )

            self.logger(f"COMPLETION: {completion}")

            if hasattr(completion, "tool_calls") and completion.tool_calls:
                if len(completion.tool_calls) > 0:
                    self.logger(f"TOOL CALLS FOUND: {completion.tool_calls}", logging.INFO)
                    await self.handle_tool_calls(completion, tool_server_map, add_responses_to_messages)
            elif completion.message:
                self.add_reply(completion.message)

        except Exception as e:
            raise MCPError(f"Failed to run tool completion: {e}") from e

    async def setup_and_run(
        self,
        configs: List[MCPServerConfig],
        tool_registry: ToolRegistry,
        add_responses_to_messages: bool = True,
    ) -> None:
        """Set up MCP servers and run tool completion.

        This function ensures the saved state exactly matches the provided server configs.
        If there's any mismatch between saved servers and provided configs, it recreates
        all servers and saves the new state.

        Args:
            configs: List of server configurations to process
            tool_registry: The tool registry to use
            add_responses_to_messages: Whether to add responses to messages

        Raises:
            MCPError: If setup or execution fails
        """
        try:
            self.logger("Setting up MCP servers...")
            tool_server_map: Dict[str, Any] = {}

            # Check if we can restore from a valid saved state
            saved_state = self.get_agent_data("mcp_state")
            can_restore = False

            if saved_state and saved_state.get("value"):
                state = saved_state["value"]
                if self.validate_state(state):
                    provided_names = self.get_server_names(configs)
                    saved_names = set(state["servers"])
                    if saved_names == provided_names:
                        can_restore = True
                        tool_server_map = await self.restore_saved_state(state, tool_registry)
                    else:
                        self.add_reply(
                            f"Saved servers {saved_names} don't match provided servers {provided_names}, recreating..."
                        )

            if not can_restore:
                tool_server_map = await self.process_new_servers(configs, tool_registry)

            await self.run_tool_completion(tool_registry, tool_server_map, add_responses_to_messages)

        except Exception as e:
            raise MCPError(f"Failed to setup and run MCP servers: {e}") from e
