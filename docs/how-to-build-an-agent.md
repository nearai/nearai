# How to build and run a python agent on NearAI

 * Install the NearAI CLI
 * Create a new folder for your agent `mkdir example_agent`
 * Create an `agent.py` file in that folder
 * Write your agent, using the environment api described below.
 * Use your agent locally using the cli
`near environment interactive example_agent --local`

## Running an existing agent from the registry
Download the agent by name
`near registry download flatirons.near/xela-agent/5`
Review the agent code before running it !!!

Run the agent locally
`near environment interactive flatirons.near/xela-agent/5`

## The environment api
Your agent will receive an `env` object that has the following methods:
 * `list_messages` - returns the list of messages in the conversation. 
You have full control to add and remove messages from this list.
 * `add_message` - adds a message to the conversation. Messages should be in the format role, content.
```json
{"role": "user", "content": "Hello, I would like to travel to Paris"}
```
Normal roles are: 
 `system`: usually your starting prompt
 `agent`:  messages from the agent (i.e. llm responses, programmatic responses)
 `user`: messages from the user
 * `request_user_input`: tell the agent that it is the user's turn, stop iterating.
 * `completion`: request inference completions from a provider and model.
Model format is `PROVIDER::MODEL`. By default the provider is Fireworks and the model is llama-3-70b-instruct.

### Additional environment tools
For working with files and running command the following functions are also available on `env`. You may call these
directly or use them through the tool_registry.
 * `list_terminal_commands` - list the history of terminal commands
 * `list_files` - list the files in the current directory
 * `get_path` - get the path of the current directory
 * `read_file` - read a file
 * `write_file` - write to a file
 * `exec_command` - execute a terminal command

### Tool registry
TODO: write this section

## Uploading an agent
 * You MUST have a folder with an `agent.py` file in it. All files in this folder will be uploaded to the registry!
 * Add a metadata file `nearai registry metadata_template example_agent`
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
 * Upload the agent `nearai registry upload example_agent`

## Running an agent remotely through the CLI
Agents can be run through the CLI using the `nearai environment run_remote` command.
A new message can be passed with the new_message argument. A starting environment (state) can be passed with the environment argument.
```shell
  nearai environment run_remote flatirons.near/example-travel-agent/1 \
  new_message="I would like to travel to Paris" \
  environment="flatirons.near/environment_run_example-travel-agent_541869e6753c41538c87cb6f681c6932/0""
 ```

## Running an agent through the API
Agents can be run through the `/environments/runs` endpoint. You will need to pass a signed message.

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
TODO: explain signed messages, point to auth code, explain how to get one manually for testing.