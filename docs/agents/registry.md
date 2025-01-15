# The Registry: Finding and Publishing Agents

NEAR AI agents can be stored in a common registry, allowing the community to share their creations.

Let's take a look at how we can navigate the registry, download agents, and contribute our own agents to the ecosystem.

!!! note
    The registry is backed by an S3 bucket with metadata stored in a database.

---

## Finding an Agent

There are two main ways to navigate the registry to find agents: through the [Web AI Hub](https://app.near.ai/agents), or using the [NEAR AI CLI](./quickstart.md):


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

<hr class="subsection" />

### Filtering Agents
You can further filter the agents by the developer that created it (`--namespace`) or the tags (`--tags`) that were added to it.

For example, to find all agents created by `gagdiez.near` with the tag `template`, you can run:

```bash
nearai registry list  --category agent \
                      --namespace gagdiez.near \
                      --tags template \
                      --show_all
```

!!! tip
    You can use the `info` command to get more details about a specific agent, for example:

    ```bash
    nearai registry info gagdiez.near/hello-ai/latest
    ```

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

## Uploading an Agent

If you created an agent and would like to share it with others, you can upload it to the registry. To upload an agent, you must have a [**logged in**](./quickstart.md#login-to-near-ai).

The `upload` command expects the path to the agent's local directory, for example:

```bash
nearai registry upload ~/.nearai/registry/<your-account.near>/<agent_folder>
```

The folder must contain an `agent.py` file, where the agent's logic is written, and a `metadata.json` file that holds information such as a description, tags, and the model used by the agent.

??? note "Example `metadata.json` file"

    ```json title="metadata.json"
    {
    "name": "hello-ai",
    "version": "0.0.1",
    "description": "A friendly agent",
    "category": "agent",
    "tags": [],
    "details": {
      "agent": {
        "defaults": {
          "model": "llama-v3p1-70b-instruct",
          "model_provider": "fireworks",
          "model_temperature": 1.0,
          "model_max_tokens": 16384
        }
      }
    },
    "show_entry": true
    }
    ```

!!! tip "Tags"
    Remember to add tags to your agent to make it easier for others to find it in the registry, for example:
    
    ```json
    { "tags": ["travel", "assistant", "vacation"] }
    ```

!!! danger
    **All files** in this folder **will be uploaded** to the registry! Make sure you are not including any sensitive data

!!! warning
    You can't remove or overwrite a file once it's uploaded, but you can hide the entire agent by setting the `"show_entry": false` field in the `metadata.json` file