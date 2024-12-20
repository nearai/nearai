# The Environment

Each time an agents executes it receives an environment, which gives it access to features such as:

* Retrieve messages in the conversation, both from the user and the agent
* Request input from the user
* Read and write files on the agent's storage
* Call other agents

---

## Interaction Messages

The messages from the current session can be accessed using the `list_messages` method:

```python
messages = env.list_messages()
print(messages)
```

??? note "Example Output"
    ```python
    [{'id': 'msg_9b676ae4ad324ca58794739d', 'content': 'Hi', 'role': 'user'},
      {'id': 'msg_58693367bcee42669a85cb69', 'content': "Hello! It's nice to meet you. Is there something I can help you with or would you like to chat?", 'role': 'assistant'},
      {'id': 'msg_16acda223c294213bc3c814e', 'content': 'help me decide how to decorate my house!', 'role': 'user'}]
    ```

Agents can add new messages to the conversation using the `add_reply` method:

```python
env.add_reply("I have finished ")
```

---

## Run Input Through a Model

The `completion` method is used to run a prompt on a specific model, using a specific provider.

<!-- Add link to models and providers -->

If only the prompt is provided, the inference will be run on the model and provider specified in the agent's metadata.

```python
messages = env.list_messages()
result = env.completion(messages)

print("Messages:", messages)
print("Result:", result)
```

??? note "Example Output"
    ```python
    Messages: [{'id': 'msg_1149aa85884b4fe8abc7d859', 'content': 'Hello', 'role': 'user'}]

    Result: Hello! It's nice to meet you. Is there something I can help you with or would you like to chat?
    ```

To run the inference on a model different from the default one, you can pass the `MODEL` or `PROVIDER::MODEL` as second argument:

```python
messages = env.list_messages()
result = env.completion([prompt] + messages, "fireworks::qwen2p5-72b-instruct")
```

??? note "Example Output"
    ```python
    Messages: [{'id': 'msg_1149aa85884b4fe8abc7d859', 'content': 'Hello', 'role': 'user'}]

    Result: Hello! How can I assist you today? Is there something specific you'd like to talk about or any questions you have?
    ```

---

## Read and Write Files

Each time an agent runs,
Agents have access to the local filesystem, allowing them to create and manipulate files.

* [`write_file(fname, content)`](api.md#nearai.agents.environment.Environment.write_file): writes content to a file in a temporary directory associated with the current conversation thread
* [`list_files(path)`](api.md#nearai.agents.environment.Environment.list_files): list the files in a path, use `.` to list the files in the agent's directory
* [`get_system_path()`](api.md#nearai.agents.environment.Environment.get_system_path): get the path of the agent's directory
* [`read_file(fname)`](api.md#nearai.agents.environment.Environment.read_file): read's a file from the temporary directory associated with the current thread, and returns its content as a string






 * [`exec_command`](api.md#nearai.agents.environment.Environment.exec_command): execute a terminal command


### Calling another agent
Other agents can be invoked with the `run_agent` method. This method takes as arguments the three parts of an agent name (owner, name, version),
accepts an optional model and query, and whether to record the agent's results on a new thread. 
* [`run_agent`](api.md#nearai.agents.environment.Environment.run_agent): call another agent

```
env.run_agent("flatirons.near", "shopper", "latest", query="NEAR cryptocurrency shirts", fork_thread=False)
```


### Additional environment methods
There are several variations for completions:

 * [`completions`](api.md#nearai.agents.environment.Environment.completions): returns the full llm response for more control
 * for tool calling completions see the [Tool registry and function Tool Calling](#tool-registry-and-function-tool-calling) section below.

For working with files and running commands the following methods are also available on `env`. You may call these
directly or use them through the tool_registry and passing them to a completions method.

 * [`list_terminal_commands`](api.md#nearai.agents.environment.Environment.list_terminal_commands): list the history of terminal commands

 * [`query_vector_store`](api.md#nearai.agents.environment.Environment.query_vector_store): query a vector store

### Logging
* [`add_system_log`](api.md#nearai.agents.environment.Environment.add_system_log): adds a system or environment log that is then saved into "system_log.txt".
* [`add_agent_log`](api.md#nearai.agents.environment.Environment.add_system_log): any agent logs may go here. Saved into "agent_log.txt".


### Tool registry and function Tool Calling
NearAI supports function based tool calling where the LLM can decide to call one of the functions (Tools) that you pass it.
You can register your own function or use any of the built-in tools (list_files, read_file, write_file, exec_command, query_vector_store, request_user_input).

The tool registry supports OpenAI style tool calling and Llama style. When a llama model is explicitly passed to completion(s)_and_run_tools
a system message is added to the conversation. This system message contains the tool definitions and instructions on how to invoke them 
using `<function>` tags.

To tell the LLM about your tools and automatically execute them when selected by the LLM, call one of these environment methods:

* [`completion_and_run_tools`](api.md#nearai.agents.environment.Environment.completion_and_run_tools): Allows tools to be passed and processes any returned tool_calls by running the tool
* [`completions_and_run_tools`](api.md#nearai.agents.environment.Environment.completions_and_run_tools): Handles tool calls and returns the full llm response.

By default, these methods will add both the LLM response and tool invocation responses to the message list. 
You do not need to call `env.add_message` for these responses.
This behavior allows the LLM to see its call then tool responses in the message list on the next iteration or next run. 
This can be disabled by passing `add_to_messages=False` to the method.


 * [`get_tool_registry`](api.md#nearai.agents.environment.Environment.get_tool_registry): returns the tool registry, a dictionary of tools that can be called by the agent. By default
it is populated with the tools listed above for working with files and commands plus [`request_user_input`](api.md#nearai.agents.environment.Environment.request_user_input). To register a function as
a new tool, call [`register_tool`](api.md#nearai.agents.tool_registry.ToolRegistry.register_tool) on the tool registry, passing it your function. 
```python
def my_tool():
    """A simple tool that returns a string. This docstring helps the LLM know when to call the tool."""
    return "Hello from my tool"

tool_registry = env.get_tool_registry()
tool_registry.register_tool(my_tool)
tool_def = tool_registry.get_tool_definition('my_tool')
response = env.completions_and_run_tools(messages, tools=[tool_def])
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



## Running an agent through the API
Agents can be run through the `/thread/runs`, `/thread/{thread_id}/runs` or  `/agent/runs` endpoints. The /thread syntax
matches the OpenAI / LangGraph API. The /agent syntax is NearAI specific.

You will need to pass a signed message to authenticate. This example uses the credentials written by `nearai login` to
your `~/.nearai/config.json` file.

```shell
auth_json=$(jq -c '.auth' ~/.nearai/config.json);

curl "https://api.near.ai/v1/threads/runs" \
      -X POST \
      --header 'Content-Type: application/json' \
      --header "Authorization: Bearer $auth_json" \
-d @- <<'EOF'
  {
    "agent_id": "flatirons.near/xela-agent/5.0.1",
    "new_message":"Build a backgammon game",
    "max_iterations": "1"
  }
EOF
```

The full message will look like this. A `thread_id` param can also be passed to continue a previous conversation. 
```shell
curl "https://api.near.ai/v1/threads/runs" \
      -X POST \
      --header 'Content-Type: application/json' \
      --header 'Authorization: Bearer {"account_id":"your_account.near","public_key":"ed25519:YOUR_PUBLIC_KEY","signature":"A_REAL_SIGNATURE","callback_url":"https://app.near.ai/","message":"Welcome to NEAR AI Hub!","recipient":"ai.near","nonce":"A_UNIQUE_NONCE_FOR_THIS_SIGNATURE"}' \
-d @- <<'EOF'
  {
    "agent_id": "flatirons.near/xela-agent/5.0.1",
    "thread_id": "a_previous_thread_id",
    "new_message":"Build a backgammon game", 
    "max_iterations": "2"
  }
EOF
```

## Remote results
The results of both run_remote and the /agent/runs endpoints are either an error or the resulting thread_id.
>"thread_579e1cf3f42742c785218106"

Threads follow the OpenAI / LangGraph api standard. `/threads/{thread_id}/messages` will return the messages on the thread.
See the full NearAI OpenAPI spec here: [https://api.near.ai/openapi.json](https://api.near.ai/openapi.json)

### Signed messages
NearAI authentication is through a Signed Message: a payload signed by a Near Account private key. (How to [Login with NEAR](login.md))

If you need one for manual testing, you can `nearai login` then copy the auth section from your `~/.nearai/config.json`.

To add signed message login to an application, see the code in hub demo [near.tsx](https://github.com/nearai/nearai/blob/main/hub/demo/src/app/_components/near.tsx).

## Saving and loading environment runs
When you are logged in, by default, each environment run is saved to the registry. You can disable this by adding the cli flag `--record_run=False`.

An environment run can be loaded by using the `--load_env` flag and passing it a registry identifier `--load_env=near.ai/environment_run_test_6a8393b51d4141c7846247bdf4086038/1.0.0`.

To list environment identifiers use the command `nearai registry list --tags=environment`.

A run can be named by passing a name to the record_run flag `--record_run="my special run"`.

Environment runs can be loaded by passing the name of a previous run to the --load_env flag like `--load_env="my special run"`.


## Running an agent with Environment Variables

When working with agents, managing configuration parameters through environment variables can provide a flexible way to adjust settings without altering the underlying code. This approach is particularly useful when dealing with sensitive information or configuration that needs to be customized without modifying the agent's codebase.

### Storing Environment Variables

Environment variables can be stored in a metadata.json file. Here’s an example of how to structure this file:

```json
{
  "details": {
    "env_vars": {
      "id": "id_from_env",
      "key": "key_from_env"
    }
  }
}
```

### Accessing Environment Variables in Code

In your agent’s code, you can access these environment variables using Python’s os module or by accessing the env_vars dictionary directly.

To retrieve an environment variable in the agent code:

```python
# Using os.environ
import os
value = os.environ.get('VARIABLE_NAME', None)

# Or using globals()
value = globals()['env'].env_vars.get('VARIABLE_NAME')
```

This allows users to fork the agent, modify the environment variables in `metadata.json`, and achieve the desired behavior without changing the code itself.

### Running the agent with Environment Variables

You can also pass environment variables directly when launching the agent. This can be useful for overriding or extending the variables defined in `metadata.json` and handling Sensitive Information: If your agent needs to interact with APIs or services that require secret keys or credentials, you can pass these as environment variables instead of hardcoding them. This ensures that sensitive information is not exposed in publicly accessible code.

To run the agent with environment variables, use the following command:

```shell
nearai agent interactive user.near/agent/1 --local --env_vars='{"foo":"bar"}'
```

####  Example

Consider an agent `zavodil.near/test-env-agent/1` that has configurable environment variables.

## Agent Frameworks
Agents can be built using a variety of frameworks and libraries. A particular bundle of libraries is given a name, such as `langgraph-0-2-26`.
To run your agent remotely with a particular framework, set the framework name in the agent's metadata.json file.
```json
{
  "details": {
    "agent": {
      "framework": "langgraph-0-2-26"
    }
  }
}
```
For local development, you can install any libraries you would like to use by adding them to top level `pyproject.toml`.

Current frameworks can be found in the repo's [frameworks](https://github.com/nearai/nearai/tree/main/nearai/aws_runner/frameworks) folder.

### LangChain / LangGraph
The example agent [langgraph-min-example](https://app.near.ai/agents/flatirons.near/langgraph-min-example/1.0.1/source)
has metadata that specifies the `langgraph-0-1-4` framework to run on langgraph version 1.4. In addition, the agent.py 
code contains an adaptor class, `AgentChatModel` that maps LangChain inference operations to `env.completions` calls.
