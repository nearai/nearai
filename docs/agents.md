# Agents
Agents are programs of varying complexity that can combine capabilities from across NearAI: 
authentication, inference, data stores, tools, apis, smart contract calls, reputation, compliance, proofs, and more.

Agents run in response to messages, usually from a user or another agent. Messages can also be sent to an agent 
from other systems such as a scheduler or indexer.

## How to build and run a python agent on NearAI
 * [Install](https://github.com/nearai/nearai/#setup) the NearAI CLI
 * Create a new folder for your agent, inside your local registry `mkdir -p ~/.nearai/registry/example_agent`
 * Create a metadata.json file for your agent `nearai registry metadata_template ~/.nearai/registry/example_agent` and edit it.
 * Create an `agent.py` file in that folder
 * Write your agent, in agent.py, using the [environment api](#the-environment-api) described below.
 * Use your agent locally using the cli and passing it a folder to write output to.
```shell
nearai environment interactive AGENT EXECUTION_FOLDER --local
```
```shell
nearai environment interactive example_agent /tmp/example_agent_run_1 --local
```

## Example agent.py
```python
# In local interactive mode, the first user input is collected before the agent runs.
prompt = {"role": "system", "content": "You are a travel agent that helps users plan trips."}
result = env.completion('llama-v3-70b-instruct', [prompt] + env.list_messages())
env.add_message("agent", result)
env.request_user_input()
```


## Running an existing agent from the registry
List all agents
```shell
nearai registry list --category agent
```

Download an agent by name
```shell
nearai registry download flatirons.near/xela-agent/5
```
⚠️ Warning: Review the agent code before running it!

### Running an agent interactively
Agents can be run interactively. The environment_path should be a folder where the agent chat record (chat.txt) and 
other files can be written, usually `~/tmp/test-agents/<AGENT_NAME>-run-X`.

* command `nearai environment interactive AGENT ENVIRONMENT_PATH`
* example 
```shell
nearai environment interactive flatirons.near/xela-agent/5 /tmp/test-agents/xela-agent-run-1
```

### Running an agent as a task
To run without user interaction pass the task input to the task

* command `nearai environment task <AGENT> <INPUT> <ENVIRONMENT_PATH>`
* example 
```shell
nearai environment task flatirons.near/xela-agent/5 "Build a command line chess engine" ~/tmp/test-agents/xela-agent/chess-engine
```


## The environment api
Your agent will receive an `env` object that has the following methods:

 * `request_user_input`: tell the agent that it is the user's turn, stop iterating.
 * `completion`: request inference completions from a provider and model.
  Model format is `PROVIDER::MODEL`. By default the provider is Fireworks and the model is llama-v3-70b-instruct.

 * `list_messages` - returns the list of messages in the conversation. 
You have full control to add and remove messages from this list.
 * `add_message` - adds a message to the conversation. Arguments are role and content.
   ```python
   env.add_message("user", "Hello, I would like to travel to Paris")
   ```
   Normal roles are: 
    *  `system`: usually your starting prompt
    *  `agent`: messages from the agent (i.e. llm responses, programmatic responses)
    *  `user`: messages from the user

### Additional environment tools
There are several variations for completions:

 * `completions`: returns the full llm response for more control
 * `completion_and_run_tools`: Allows tools to be passed and processes any returned tool_calls by running the tool
 * `completions_and_run_tools`: Both tool calls and returns the full llm response.


For working with files and running commands the following functions are also available on `env`. You may call these
directly or use them through the tool_registry and passing them to a completions method.

 * `list_terminal_commands` - list the history of terminal commands
 * `list_files` - list the files in the current directory
 * `get_path` - get the path of the current directory
 * `read_file` - read a file
 * `write_file` - write to a file
 * `exec_command` - execute a terminal command

### Tool registry
 * `get_tool_registry`: returns the tool registry, a dictionary of tools that can be called by the agent. By default
it is populated with the tools listed above for working with files and commands plus `request_user_input`. To register a function as
a new tool, call `register_tool` on the tool registry, passing it your function. 
```python
def my_tool():
    """A simple tool that returns a string. This docstring helps the LLM know when to call the tool."""
    return "Hello from my tool"

env.get_tool_registry().register_tool(my_tool)

response = env.completions_and_run_tools("llama-v3p1-405b-instruct", messages, tools=get_tool_registry().get_all_tools())
```

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
  "details": {},
  "show_entry": true,
  "name": "example-travel-agent",
  "version": "5"
}
```

 * You must be logged in to upload, `nearai login`
 * Upload the agent `nearai registry upload ~/.nearai/registry/example_agent`

## Running an agent remotely through the CLI
Agents can be run through the CLI using the `nearai environment run_remote` command.
A new message can be passed with the new_message argument. A starting environment (state) can be passed with the environment_id argument.
```shell
  nearai environment run_remote flatirons.near/example-travel-agent/1 \
  new_message="I would like to travel to Paris" \
  environment_id="flatirons.near/environment_run_example-travel-agent_541869e6753c41538c87cb6f681c6932/0""
 ```

## Running an agent through the API
Agents can be run through the `/environments/runs` endpoint. You will need to pass a signed message to authenticate.

```shell
curl "https://api.near.ai/v1/environment/runs" \
      -X POST \
      --header 'Content-Type: application/json' \
      --header 'Authorization: Bearer {"account_id":"flatirons.near","public_key":"ed25519:F5DeKFoyF1CQ6wG6jYaXxwQeoksgi8a677JkniDBGBTB","signature":"kfiH7AStKrBaMXzwpE50yQ2TRTxksID9tNVEdazxtegEu6rwH6x575smcAJPAUfTtlT2l7xwXtapQkxd+vFUAg==","callback_url":"http://localhost:3000/","message":"Welcome to NEAR AI Hub!","recipient":"ai.near","nonce":"00000000000000000005722050769950"}' \
-d @- <<'EOF'
  {
    "agent_id": "flatirons.near/xela-agent/5",
    "new_message":"Build a backgammon game", 
    "max_iterations": "2"
  }
EOF
```

### Signed messages
NearAI authentication is through a Signed Message: a payload signed by a Near Account private key.

If you need one for manual testing, you can `nearai login` then copy the auth section from your `~/.nearai/config.json`.

To add signed message login to an application, see the code in hub demo [near.tsx](https://github.com/nearai/nearai/blob/main/hub/demo/src/app/_components/near.tsx).

## Saving and loading environment runs
When you are logged in, by default, each environment run is saved to the registry. You can disable this by adding the cli flag `--record_run=False`.

An environment run can be loaded by using the `--load_env` flag and passing it a registry identifier `--load_env=near.ai/environment_run_test_6a8393b51d4141c7846247bdf4086038/1.0.0`.

To list environment identifiers use the command `nearai registry list --tags=environment`.

A run can be named by passing a name to the record_run flag `--record_run="my special run"`.

Environment runs can be loaded by passing the name of a previous run to the --load_env flag like `--load_env="my special run"`.