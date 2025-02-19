# Hub Secrets (WIP)

Secrets enhance the agent framework by allowing both the **agent author** and the **agent user** to send private information to the runner, which is managed and executed by the NEAR AI platform.

- **Reading Secrets**: To read secrets, **user authentication** via a NEAR account is required.
- **Secrets Distribution**: Secrets are only provided to our runner.
- **Secrets Encryption**: Secrets are encrypted in the database using a master key (in progress).

---

## Agent and User Variables

### Agent Public Variables
- Defined in `metadata.json/details/env_vars` by the agent author.  
- Publicly available parameters, which can be changed during updates or forks.  
**Example**: `api_url`

### User Public Variables
- Provided by the user via CLI or URL parameters.  
**Example**: `refId` in a URL such as  
  `https://app.near.ai/agents/casino.near/game/1?refId=ad.near`

---

### Agent Private Variables
- Secrets added by the **agent author** for their agent.  
**Example**: `GITHUB_API_TOKEN`

### User Private Variables
- Secrets added by the **user** for a specific agent (if required by the agent author).  
**Example**: `private_key`

---

## How These Variables Combine
All agent and user data end up together in `env_vars` (the environment) as a single key-value object. If multiple agents are running, each agent can only see its own secrets.

### Priority of Records
1. **Agent Public Vars** (lowest priority)  
2. **Agent Private Vars**  
3. **User Public Vars**  
4. **User Private Vars** (highest priority)

If two variables share the same key, the higher-priority entry will override the lower-priority one.

---

## Current Endpoints

Below are the three key endpoints for managing Hub Secrets. All routes require user authentication, typically provided via `Authorization: Bearer <YOUR-NEAR-ACCOUNT-TOKEN>`.

### 1. `GET /v1/get_user_secrets`

Retrieves secrets belonging to the authenticated user (via `owner_namespace`).

**Query Parameters**  
- `limit` (`int`, optional, default `100`): Maximum number of secrets to return.  
- `offset` (`int`, optional, default `0`): Offset for pagination.  

**Example Request**  
```bash
curl -X GET "https://<api-url>/v1/get_user_secrets?limit=10&offset=0" \
  -H "Authorization: Bearer <YOUR-NEAR-ACCOUNT-TOKEN>"
```

Example response
```json
[
  {
    "id": 123,
    "owner_namespace": "your_account.near",
    "namespace": "example_agent",
    "name": "my_secret_name",
    "version": "1.0",
    "key": "GITHUB_API_TOKEN",
    "category": "agent",
    "created_at": "2025-02-19T12:34:56.789Z",
    "updated_at": "2025-02-19T12:34:56.789Z"
  }
]
```

2. POST /v1/create_hub_secret
Creates a new hub secret.
Secrets can be tied to:

A specific agent namespace (namespace)
A specific version (version) (optional)
A category, such as "agent" or "user" (default is "agent")

**Example Request Body**  
```json
{
  "namespace": "string",      // Required
  "name": "string",           // Required
  "version": "string",        // Optional
  "description": "string",    // Optional
  "key": "string",            // Required
  "value": "string",          // Required
  "category": "string"        // Optional (default: "agent")
}
```

### Example Request 

```bash
curl -X POST "https://<api-url>/v1/create_hub_secret" \
  -H "Authorization: Bearer <YOUR-NEAR-ACCOUNT-TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "namespace": "example_agent",
    "name": "my_secret_name",
    "version": "1.0",
    "description": "GitHub token for my agent",
    "key": "GITHUB_API_TOKEN",
    "value": "ghp_abc123",
    "category": "agent"
  }'
```

Example Response

```json
true
```

3. POST /v1/remove_hub_secret
Removes an existing hub secret from the database.

**Example Request Body**  
```json
{
  "namespace": "string",  // Required
  "name": "string",       // Required
  "version": "string",    // Optional
  "key": "string",        // Required
  "category": "string"    // Optional (default: "agent")
}
```

### Example Request

```bash
curl -X POST "https://<api-url>/v1/remove_hub_secret" \
  -H "Authorization: Bearer <YOUR-NEAR-ACCOUNT-TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "namespace": "example_agent",
    "name": "my_secret_name",
    "version": "1.0",
    "key": "GITHUB_API_TOKEN",
    "category": "agent"
  }'
```

Example Response
```json
true
```