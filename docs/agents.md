# Agents

<b>Quickest start</b>, this script runs the Quickstart commands below.
```shell
docs/agent_quickstart.sh
```

## QUICKSTART: build and run a python agent on NearAI
1. [Install](https://github.com/nearai/nearai/#setup) the NearAI CLI.

2. Create a new folder for your agent; 

    we recommend placing it inside your local registry `mkdir -p ~/.nearai/registry/example_agent`. 

3. Create a metadata.json file for your agent

   `nearai registry metadata_template ~/.nearai/registry/example_agent agent "Example agent"` and edit it.

4. Create an `agent.py` file in that folder.
     * Write your agent, in agent.py, using the [environment API](#the-environment-api) described below.
     * Or paste in the [example agent.py](#example-agentpy) below.

5. Run your agent locally using the cli and passing it a folder to write output to. 
```shell
nearai agent interactive example_agent /tmp/example_agent_run_1 --local
```

### Example agent.py
```python
# In local interactive mode, the first user input is collected before the agent runs.
prompt = {"role": "system", "content": "You are a travel agent that helps users plan trips."}
result = env.completion([prompt] + env.list_messages())
env.add_message("agent", result)
env.request_user_input()
```

## About Agents
Agents are programs of varying complexity that can combine capabilities from across NearAI:
authentication, inference, data stores, tools, apis, smart contract calls, reputation, compliance, proofs, and more.

Agents run in response to messages, usually from a user or another agent. Messages can also be sent to an agent
from other systems such as a scheduler or indexer.


## Agent Operation and Features:
* `interactive` mode runs the agent in an infinite loop until: it is terminated by typing "exit" in the chat; is forcibly exited with a code; or stopped by the user with "Ctrl+C".
* The execution folder is optional; by default, the initial agent's folder may be used instead.
* If you use a folder other than the local registry, provide the full path to the agent instead of just the agent name.

Command: 
```
nearai agent interactive AGENT [EXECUTION_FOLDER] --local
```
Example:
```shell
nearai agent interactive example_agent --local
```

* The agent can save temporary files to track the progress of a task from the user in case the dialogue execution is interrupted. By default, the entire message history is stored in a file named `chat.txt`. The agent can add messages there by using [`env.add_message()`](api.md#nearai.environment.Environment.add_message). Learn more about [the environment API](#the-environment-api).
* During its operation, the agent creates a file named `.next_agent`, which stores the role of the next participant expected in the dialogue (either `user` or `agent`) during the next iteration of the loop. The agent can control this value using [`env.set_next_actor()`](api.md#nearai.environment.Environment.set_next_actor).
* The agent can use local imports from the home folder or its subfolders. It is executed from a temporary folder within a temporary environment.



## Running an existing agent from the registry
List all agents
```shell
nearai registry list --category agent
```

Download an agent by name
```shell
nearai registry download flatirons.near/xela-agent/5
```

The `--force` flag allows you to overwrite the local agent with the version from the registry.

⚠️ Warning: Review the agent code before running it!

### Running an agent interactively
Agents can be run interactively. The environment_path should be a folder where the agent chat record (chat.txt) and 
other files can be written, usually `~/tmp/test-agents/<AGENT_NAME>-run-X`.

* command `nearai agent interactive AGENT ENVIRONMENT_PATH`
* example 
```shell
nearai agent interactive flatirons.near/xela-agent/5 /tmp/test-agents/xela-agent-run-1
```

### Running an agent as a task
To run without user interaction pass the task input to the task

* command `nearai agent task <AGENT> <INPUT> <ENVIRONMENT_PATH>`
* example 
```shell
nearai agent task flatirons.near/xela-agent/5 "Build a command line chess engine" ~/tmp/test-agents/xela-agent/chess-engine
```


## The Environment API
Your agent will receive an `env` object that has the following methods:

  * [`request_user_input`](api.md#nearai.environment.Environment.request_user_input): tell the agent that it is the user's turn, stop iterating.
  * [`completion`](api.md#nearai.environment.Environment.completion): request inference completions from a provider and model.
The model format can be either `PROVIDER::MODEL` or simply `MODEL`. By default the provider is `fireworks` and the model is `llama-v3p1-405b-instruct-long`. The model can be passed into `completion` function or as an agent metadata:
   ```json
   "details": {
     "agent": {
       "defaults": {
         // All fields below are optional.
         "model": "llama-v3p1-405b-instruct-long",
         "model_max_tokens": 16384,
         "model_provider": "fireworks",
         "model_temperature": 1.0
       }
     }
   }
   ```
  * [`list_messages`](api.md#nearai.environment.Environment.list_messages): returns the list of messages in the conversation. 
You have full control to add and remove messages from this list.
  * [`add_message`](api.md#nearai.environment.Environment.add_message): adds a message to the conversation. Arguments are role and content.
   ```python
   env.add_message("user", "Hello, I would like to travel to Paris")
   ```
   Normal roles are: 
    *  `system`: usually your starting prompt
    *  `agent`: messages from the agent (i.e. llm responses, programmatic responses)
    *  `user`: messages from the user

### Additional environment tools
There are several variations for completions:

 * [`completions`](api.md#nearai.environment.Environment.completions): returns the full llm response for more control
 * [`completion_and_run_tools`](api.md#nearai.environment.Environment.completion_and_run_tools): Allows tools to be passed and processes any returned tool_calls by running the tool
 * [`completions_and_run_tools`](api.md#nearai.environment.Environment.completions_and_run_tools): Both tool calls and returns the full llm response.


For working with files and running commands the following functions are also available on `env`. You may call these
directly or use them through the tool_registry and passing them to a completions method.

 * [`list_terminal_commands`](api.md#nearai.environment.Environment.list_terminal_commands): list the history of terminal commands
 * [`list_files`](api.md#nearai.environment.Environment.list_files): list the files in the current directory
 * [`get_path`](api.md#nearai.environment.Environment.get_path): get the path of the current directory
 * [`read_file`](api.md#nearai.environment.Environment.read_file): read a file
 * [`write_file`](api.md#nearai.environment.Environment.write_file): write to a file
 * [`exec_command`](api.md#nearai.environment.Environment.exec_command): execute a terminal command

### Tool registry
 * [`get_tool_registry`](api.md#nearai.environment.Environment.get_tool_registry): returns the tool registry, a dictionary of tools that can be called by the agent. By default
it is populated with the tools listed above for working with files and commands plus [`request_user_input`](api.md#nearai.environment.Environment.request_user_input). To register a function as
a new tool, call [`register_tool`](api.md#nearai.tool_registry.ToolRegistry.register_tool) on the tool registry, passing it your function. 
```python
def my_tool():
    """A simple tool that returns a string. This docstring helps the LLM know when to call the tool."""
    return "Hello from my tool"

env.get_tool_registry().register_tool(my_tool)

response = env.completions_and_run_tools("llama-v3p1-405b-instruct-long", messages, tools=get_tool_registry().get_all_tools())
```

### Logging
* [`add_system_log`](api.md#nearai.environment.Environment.add_system_log): adds a system or environment log that is then saved into "system_log.txt".
* [`add_agent_log`](api.md#nearai.environment.Environment.add_system_log): any agent logs may go here. Saved into "agent_log.txt".

## Uploading an agent
 * You need a folder with an `agent.py` file in it, `~/.nearai/registry/example_agent` in this example. 
 * The agent may consist of additional files in the folder.

   ⚠️ Warning: All files in this folder will be uploaded to the registry!
 * Add a metadata file `nearai registry metadata_template ~/.nearai/registry/example_agent`
 * Edit the metadata file to include the agent details
```json
{
  "category": "agent",
  "description": "An example agent that gives travel recommendations",
  "tags": [
    "python",
    "travel"
  ],
  "details": {
    "agent": {
       "defaults": {
         // All fields below are optional.
         "model": "llama-v3p1-405b-instruct-long",
         "model_max_tokens": 16384,
         "model_provider": "fireworks",
         "model_temperature": 1.0
       }
     }
  },
  "show_entry": true,
  "name": "example-travel-agent",
  "version": "0.0.5"
}
```

 * You must be [logged in with NEAR](login.md) to upload, `nearai login`
 * Upload the agent `nearai registry upload ~/.nearai/registry/example_agent`

⚠️ You can't remove or overwrite a file once it's uploaded, but you can hide the entire agent by setting the `"show_entry": false` field.

## Running an agent remotely through the CLI
Agents can be run through the CLI using the `nearai agent run_remote` command.
A new message can be passed with the new_message argument. A starting environment (state) can be passed with the environment_id argument.

```shell
  nearai agent run_remote flatirons.near/example-travel-agent/1 \
  new_message="I would like to travel to Brazil"
```

This environment already contains a request to travel to Paris and an agent response.
A new_message could be included to further refine the request. In this example without a new_message the agent will
reprocess the previous response and follow up about travel to Paris.

```shell
  nearai agent run_remote flatirons.near/example-travel-agent/1 \
  environment_id="flatirons.near/environment_run_flatirons.near_example-travel-agent_1_1c82938c55fc43e492882ee938c6356a/0"
```

## Running an agent through the API
Agents can be run through the `/agent/runs` endpoint. 
You will need to pass a signed message to authenticate. This example uses the credentials written by `nearai login` to
your `~/.nearai/config.json` file.

```shell
auth_json=$(jq -c '.auth' ~/.nearai/config.json);

curl "https://api.near.ai/v1/agent/runs" \
      -X POST \
      --header 'Content-Type: application/json' \
      --header "Authorization: Bearer $auth_json" \
-d @- <<'EOF'
  {
    "agent_id": "flatirons.near/xela-agent/5",
    "new_message":"Build a backgammon game",
    "max_iterations": "2"
  }
EOF
```

The full message will look like this. An `environment_id` param can also be passed to continue a previous run. 
```shell
curl "https://api.near.ai/v1/agent/runs" \
      -X POST \
      --header 'Content-Type: application/json' \
      --header 'Authorization: Bearer {"account_id":"your_account.near","public_key":"ed25519:YOUR_PUBLIC_KEY","signature":"A_REAL_SIGNATURE","callback_url":"https://app.near.ai/","message":"Welcome to NEAR AI Hub!","recipient":"ai.near","nonce":"A_UNIQUE_NONCE_FOR_THIS_SIGNATURE"}' \
-d @- <<'EOF'
  {
    "agent_id": "flatirons.near/xela-agent/5",
    "environment_id": "a_previous_environment_id",
    "new_message":"Build a backgammon game", 
    "max_iterations": "2"
  }
EOF
```

## Remote results
The results of both run_remote and the /agent/runs endpoint are either an error or the resulting environment state.
>Agent run finished. New environment is "flatirons.near/environment_run_flatirons.near_example-travel-agent_1_1c82938c55fc43e492882ee938c6356a/0"

To view the resulting state, download the `environment.tar.gz` file from the registry and extract it.
```shell
nearai registry download flatirons.near/environment_run_flatirons.near_example-travel-agent_1_1c82938c55fc43e492882ee938c6356a/0
```


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
Agents can be built using a variety of frameworks and libraries. A particular bundle of libraries is given a name, such as `langgraph-1-4`.
To run your agent remotely with a particular framework, set the framework name in the agent's metadata.json file.
```json
{
  "details": {
    "agent": {
      "framework": "langgraph-1-4"
    }
  }
}
```
For local development, you can install any libraries you would like to use by adding them to top level `pyproject.toml`.

Current frameworks can be found in the repo's [frameworks](https://github.com/nearai/nearai/tree/main/aws_runner/frameworks) folder.

### LangChain / LangGraph
The example agent [langgraph-min-example](https://app.near.ai/agents/flatirons.near/langgraph-min-example/1.0.1/source)
has metadata that specifies the `langgraph-1-4` framework to run on langgraph version 1.4. In addition, the agent.py 
code contains an adaptor class, `AgentChatModel` that maps LangChain inference operations to `env.completions` calls.