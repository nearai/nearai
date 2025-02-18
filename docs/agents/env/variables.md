# Secrets & Environment Variables

Secrets and environment variables provide a flexible way to manage configuration settings and sensitive information in your agents without modifying the source code. An agent has access to two main types of input variables:

1. **Agent Variables**: Set by the agent author
2. **User Variables**: Set by the end user of an agent

Each of which can be either public or private.

- [**Public Variables**](#public-environment-variables): For general configuration settings or user tracking
- [**Private Variables or Secrets**](#secrets): For sensitive information like API keys

---

## Public Variables

Public environment variables are variables that are set by the agent author and are publicly visible and modifiable during updates/forks. These are typically used for general configuration settings or public user information. There are two types of public environment variables, ones set by the agent author and ones set by the user.

- **Agent Public Variables** 
      - Set by the agent author in the `metadata.json` file
      - Publicly visible and modifiable during updates/forks
      - Example: A URL of an API endpoint

- **User Public Variables**
    - Provided by users via CLI or URL parameters
    - Example: A user could pass an URL referrer ID to an agent to track where the agent is being used


### Agent Public Variables

An agent's public variables are stored in the agent's `metadata.json` file.

Example:

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

### User Public Variables

<!-- TODO: Need more information on how user public variables are stored and passed to an agent. Is the CLI reference regarding the --env_vars flag? If so, that might be better left to the secrets section as it is more relevant to secrets. -->

User public variables are passed to an agent when running the agent locally via CLI or via URL parameters.

For example, a user could pass a URL referrer ID to an agent to track where the agent is being referred from.

```bash
refId in https://app.near.ai/agents/casino.near/game/1?refId=ad.near
```
<!-- 
TODO: explain this better... I believe they are combined at some point into one large env_vars object. -->

These variables are also stored in an `env_vars` object but seprate from an agent's `metadata.json` file.

---

## Secrets

<!-- TODO: add more detailed explainer about the aws runner and how it works -->

Secrets enhance the agent framework by allowing both an agent and its user to send private information to the execution environment (an aws runner). Some important information to note:

- **Reading Secrets**: Requires user authentication via a NEAR account
- **Secret Distribution**: Secrets are only provided to our trusted runner
- **Secret Encryption**: All secrets are encrypted in the database using a master key

Just like public environment variables, there are two types of secrets; ones set by the agent author and ones set by the user.

- **Agent Secrets**
    - Set by the agent author in the AI Developer Hub
    - Can be version-specific or apply to all versions
    - Example: `Github_API_Token`

- **User Secrets**
    - Set by users for specific agents when required in the AI Developer Hub
    - Example: `signer_private_key` for making crypto transactions

### Managing Secrets

<!-- TODO: Add more information about how secrets are stored in the AI platform / runner  -->

Secrets are securely stored in the NEAR AI platform, not in the agent's codebase. They are securely accessed by agents via the [Secrets API endpoints](#secrets-api).

### Managing Secrets in the Developer Hub

The easiest way to manage secrets is via the [NEAR AI Developer Hub](https://app.near.ai).

  1.) In the Agent Development Hub, select an agent and click on the `Run` tab.

  2.) On the right side of the page, you will see `Environment Variables`, click `+` to create a new secret.

![secrets-1](../../assets/agents/secrets-1.png)

  3.) You will be prompted to enter the secret's key value pair.

![secrets-2](../../assets/agents/secrets-2.png)

### Using a secret locally

You can use a secret locally by passing it to the agent when launching it. Note that this will only be accesible to the agent for the duration of that run.

```bash
nearai agent <FULL_PATH_TO_AGENT> --local --env_vars='{"foo":"bar"}'
```

---

## Using Variables & Secrets

Once stored, agents can access variables & secrets using several methods:

<!-- TODO: Add more info here about the differences between these three methods -->

```python
# Using env.env_vars
value = env.env_vars.get('VARIABLE_NAME', 'default_value')

# Using os.environ
import os
value = os.environ.get('VARIABLE_NAME', 'default_value')

# Or using globals()
value = globals()['env'].env_vars.get('VARIABLE_NAME', 'default_value')
```

### Secrets API

<!-- TODO: How to access secrets API and how this works securely -->

Agents can access secrets securley from the runner using the following API endpoints:

| Endpoint | Method | Description |
|----------|---------|------------|
| `/v1/get_user_secrets` | GET | Retrieve user secrets |
| `/v1/create_hub_secret` | POST | Create a new secret |
| `/v1/remove_hub_secret` | POST | Delete an existing secret |


!!! warning
    When multiple agents are running, each agent only has access to its own secrets.

<!-- TODO: Is this the best place for this Variable Resolution section? -->

## Variable Resolution

!!! tip "Priority Order"
    All variables are combined into a single `env_vars` object with the following priority (highest to lowest):

    1. User Public Variables
    2. User Private Variables (Secrets)
    3. Agent Public Variables
    4. Agent Private Variables (Secrets)
