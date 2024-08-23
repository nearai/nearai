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

   `nearai registry metadata_template ~/.nearai/registry/example_agent` and edit it.

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
result = env.completion('llama-v3-70b-instruct', [prompt] + env.list_messages())
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

* The agent can save temporary files to track the progress of a task from the user in case the dialogue execution is interrupted. By default, the entire message history is stored in a file named `chat.txt`. The agent can add messages there by using `env.add_message()`. Learn more about [the environment API](#the-environment-api).
* During its operation, the agent creates a file named `.next_agent`, which stores the role of the next participant expected in the dialogue (either `user` or `agent`) during the next iteration of the loop. The agent can control this value using `env.set_next_actor()`.
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

 * `request_user_input`: tell the agent that it is the user's turn, stop iterating.
 * `completion`: request inference completions from a provider and model.
The model format can be either `PROVIDER::MODEL` or simply `MODEL`. By default the provider is `Fireworks` and the model is `llama-v3-70b-instruct`.

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
Agents can be run through the `/agent/runs` endpoint. You will need to pass a signed message to authenticate.

```shell
curl "https://api.near.ai/v1/agent/runs" \
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