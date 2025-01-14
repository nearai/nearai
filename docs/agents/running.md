# Running an Agent

Agents can be run locally or remotely. When running locally, you can run them interactively or as a task. When running remotely, you can use the NEAR AI API to run them.

## Running the Agent Locally

You can execute it in two different ways: interactively or as a task.

Know that you can also run agents **directly on the [Web AI Hub](https://app.near.ai/agents)**, you don't need to download an agent if you just want to see how they work.

!!! danger "Always Review the Code"
    Agents can execute arbitrary code on your machine, so please always review the agent's code before running it!
    
    By default, you will find the agent's code on the local directory `~/.nearai/registry`, there, check the agent's `agent.py` file either by using the `cat` command or opening it in a text editor.

    ```bash
    # Checking gagdiez.near/hello-ai/latest code
    cd ~/.nearai/registry/gagdiez.near/hello-ai/latest
    cat agent.py
    ```

<hr class="subsection">

### Interactive Run

Interactive runs execute the agent on a loop, allowing you to chat with it interactively until you decide to exit (using the `exit` command), or quit the session using `ctrl+c`.

```bash
# Download the agent from the registry
nearai registry download gagdiez.near/hello-ai/latest

# Running the agent by absolute path
nearai agent interactive ~/.nearai/registry/gagdiez.near/hello-ai/latest --local
```

<hr class="subsection">

### Running as a Task
When running an agent as a task, we simply provide an input and let the agent execute it without any user interaction.

```bash
nearai agent task ~/.nearai/registry/gagdiez.near/hello-ai/latest "write a poem about the sorrow of losing oneself, but end on a positive note" --local
```

---

## Running the Agent Remotely

Agents can be run through the `/thread/runs`, `/thread/{thread_id}/runs` or  `/agent/runs` endpoints. The /thread syntax
matches the OpenAI / LangGraph API. The /agent syntax is NEAR AI specific.

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

??? tip "Remote results"
    The results of the /agent/runs endpoints are either an error or the resulting thread_id.
    >"thread_579e1cf3f42742c785218106"

    Threads follow the OpenAI / LangGraph api standard. `/threads/{thread_id}/messages` will return the messages on the thread.
    See the full NEAR AI OpenAPI spec here: [https://api.near.ai/openapi.json](https://api.near.ai/openapi.json)
