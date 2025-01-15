# Hub Secrets (WIP)

Secrets enhance the agent framework by allowing both the agent author and the agent user to send private information to the runner, which is managed and executed by us.

- Reading Secrets: To read secrets, user authentication via an NEAR account is required.
- Secrets Distribution: Secrets are only provided to our runner.
- Secrets Encryption: Secrets are encrypted in the database using a master key.

--- 

The agent has two types of input variables: agent variables and user variables. Each type has public and secret variables.

### Agent public vars

`metadata.json/details/env_vars` - Provided by the agent author. These are publicly available parameters that can be modified during updates or forks. 
For example: `api_url`.

### User public vars

`env_vars` - Provided by the user via CLI or URL parameter. 
For example: `refId` in https://app.near.ai/agents/casino.near/game/1?refId=ad.near

---
We add secrets (which can be added for all versions of the agent or for a specific one).


### Agent private vars 

The agent author can add a secret for their agent. 
For example: `Github_API_Token`.

### User private vars

The user can add a secret for a specific agent (if required by the agent author). 
For example: `private_key`.

---

In the end, all these data end up in env_vars as a single key-value object. If multiple agents are running, each agent only sees its own secrets.

### Priority of Records:

- agent_vars: Agent variables from metadata have a lower priority than agent secrets.
- user_vars: User variables from URL/CLI have a higher priority than user secrets.
- final vars: User variables have a higher priority than agent variables.

### Current endpoints 

- api-url/v1/hub_secrets (GET)
- api-url/v1/create_hub_secret (POST)
- api-url/v1/remove_hub_secret (POST)