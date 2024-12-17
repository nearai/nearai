# The Registry: Finding and Running Agents

NearAI agents can be stored in a common registry, allowing users to share their agents with others. Let's take a look at how we can navigate the registry, download agents, and contribute our own agents to the ecosystem.

---

## Finding an Agent

There are two main ways to navigate the registry to find agents: through the [Web AI Hub](https://app.near.ai/agents), or using the [NearAI CLI](./agents/quickstart.md):


```bash
# List all agents
nearai registry list --category agent
```

??? experiment "Example Output"

    ```shell
    ┌─────────────────────────────────┬─────────────────────────┬───────┐
    │ entry                           │ description             │ tags  │
    ├─────────────────────────────────┼─────────────────────────┼───────┤
    │ zavodil.near/ai16z-docs/1.03    │ AI agent with AI16Z ... │ agent │
    ├─────────────────────────────────┼─────────────────────────┼───────┤
    │ flatirons.near/common-tool...   │ A library of common ..  │ llama │
    ├─────────────────────────────────┼─────────────────────────┼───────┤
    │ jayzalowitz.near/example_a...   │ Example agent           │       │
    ├─────────────────────────────────┼─────────────────────────┼───────┤
    │ ...                             │ ...                     │ ...   │
    └─────────────────────────────────┴─────────────────────────┴───────┘
    ```

!!! tip
    You can run the agents **directly on the [Web AI Hub](https://app.near.ai/agents)** to see how they work

---

## Downloading an Agent

Once you find an agent that you would like to download, you can use the `download` command to pull it down to your local machine. The command expects an agent of the form:

```bash
nearai registry download <account.near>/<agent_name>/<version>
```

Where version can be a specific version number, or `latest` to download the most recent version, for example: 

```bash 
# Download a hello world agent
nearai registry download gagdiez.near/hello-ai/latest
```

By default, the agent will be **downloaded to the `~/.nearai/registry` local directory**, for example the agent above will be downloaded to `~/.nearai/registry/gagdiez.near/hello-ai/latest`.

!!! tip
    The `--force` flag allows you to overwrite the local agent with the version from the registry.

---

## Running the Agent Locally

After downloading an agent you can execute it in two different ways: interactively or as a task.

Know that you can also run agents **directly on the [Web AI Hub](https://app.near.ai/agents)**, you don't need to download an agent if you just want to see how they work.

!!! danger "Always Review the Code"
    Agents can execute arbitrary code on your machine, so please always review the agent's code before running it!
    
    By default, you will find the agent's code on the local directory `~/.nearai/registry`, there, check the agent's `agent.py` file either by using the `cat` command or opening it in a text editor.

    ```bash
    # Checking gagdiez.near/hello-ai/latest code
    cd ~/.nearai/registry/gagdiez.near/hello-ai/latest
    cat agent.py
    ```

<hr style="width: 80%; margin: 0 auto;">

### Interactive Run

Interactive runs execute the agent on a loop, allowing you to chat with it interactively until you decide to exit (using the `exit` command), or quit the session using `ctrl+c`.

```bash
# Running the agent by absolute path
nearai agent interactive ~/.nearai/registry/gagdiez.near/hello-ai/latest --local
```

<hr style="width: 80%; margin: 0 auto;">

### Running as a Task
When running an agent as a task, we simply provide an input and let the agent execute it without any user interaction.

```bash
nearai agent task ~/.nearai/registry/gagdiez.near/hello-ai/latest "write a poem about the sorrow of loosing oneself, but end on a positive note" --local
```

---

## Running an Agent Remotely

Agents that are in the registry can be run through the CLI using the `nearai agent run_remote` command.

```shell
  nearai agent run_remote gagdiez.near/hello-ai/latest --new_message="I would like you to write a short song"
```

<!-- TODO: Clarify this, I do not understand how it works given that I did not manage to make it work -->

Running an agent remotely will create a thread on the NearAI platform, where the agent will execute the provided input. The `new_message` flag is used to provide the agent with a prompt request.

The results of `run_remote` is either an error or the resulting thread_id (e.g. `"thread_579e1cf3f42742c785218106"`) which can be used to retrieve the conversation.

Threads follow the OpenAI / LangGraph api standard. `/threads/{thread_id}/messages` will return the messages on the thread.
See the full NearAI OpenAPI spec here: [https://api.near.ai/openapi.json](https://api.near.ai/openapi.json)

<!-- A new_message could be included to further refine the request. In this example without a new_message the agent will
reprocess the previous response and follow up about travel to Paris. 

```shell
  nearai agent run_remote flatirons.near/example-travel-agent/1 \
  environment_id="flatirons.near/environment_run_flatirons.near_example-travel-agent_1_1c82938c55fc43e492882ee938c6356a/0"
```
-->

---

## Uploading an Agent

If you created an agent and would like to share it with others, you can upload it to the registry. To upload an agent, you must have a [**logged in**](./agents/quickstart.md#login-to-nearai).

The `upload` command expects the path to the agent's local directory, for example:

```bash
nearai registry upload ~/.nearai/registry/<your-account.near>/<agent_folder>
```

The folder must contain an `agent.py` file, where the agent's logic is written, and a `metadata.json` file that holds information such as a description, tags, and the model used by the agent.

!!! tip "Tags"
    Remember to add tags to your agent to make it easier for others to find it in the registry, for example:
    
    ```json
    { "tags": ["travel", "assistant", "vacation"] }
    ```

!!! danger
    **All files** in this folder **will be uploaded** to the registry! Make sure you are not including any sensitive data

!!! warning
    You can't remove or overwrite a file once it's uploaded, but you can hide the entire agent by setting the `"show_entry": false` field in the `metadata.json` file
