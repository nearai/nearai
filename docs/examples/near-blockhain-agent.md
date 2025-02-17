---
title: NEAR Blockchain Agent Example
description: A complete example of a NEAR blockchain agent implementation
---

# NEAR Blockchain Agent Example

!!! note "Source Code"
    Full source code for this example is at the [bottom of this page](#complete-agent-code) and 
    also available on [Github](https://github.com/nearai/official-agents/tree/main/near-agent) 
    
This example demonstrates how to build an AI agent that can interacts with the NEAR blockchain. This agent can perform account operations, token transfers, and staking actions.

## Features

- 🔐 Account Management
- 💸 NEAR Transfers
- 📊 Token Balance Checking
- 🎨 NFT Viewing
- 🏦 Staking Operations

## Implementation

### State Management

The agent uses an enum to track possible actions:

```python
class Actions(enum.Enum):
    GET_USER_DATA = "GET_USER_DATA"
    NEAR_SHOW_ACCOUNT = "NEAR_SHOW_ACCOUNT"
    NEAR_TRANSFER = "NEAR_TRANSFER"
    NEAR_STAKE = "NEAR_STAKE"
```

### Authentication 

!!! warning "Security"
    
    Store your private key securely using environment variables! See [Secrets](../agents/secrets.md) for more information.

```python
signer_private_key = globals()['env'].env_vars.get("signer_private_key", None)
```


### Core Agent Logic

```python
async def agent(env: Environment, state: State):
    if not signer_private_key:
        env.add_reply("Add a secret `signer_private_key`...")
```

---

## Usage Examples

### Viewing Account Details

```python
# State configuration for account view
state.action = Actions.NEAR_SHOW_ACCOUNT
```

Example response:
```
Your account is example.near
Your account balance is 100 NEAR
```

### Making Transfers

```python
# Configure transfer state
state.action = Actions.NEAR_TRANSFER
state.receiver_id = "recipient.near"
state.amount = 1.0
```

### Staking NEAR

```python
# Configure staking state
state.action = Actions.NEAR_STAKE
state.receiver_id = "validator.near"
state.amount = 10.0
```

## Best Practices

1. **Error Handling**
   - Always validate user inputs
   - Check account balances before transfers
   - Handle network errors gracefully

2. **Security**
   - Never hardcode private keys
   - Use environment variables for sensitive data
   - Validate transaction parameters

3. **State Management**
   - Reset state after successful actions
   - Maintain clear state transitions
   - Document state changes

!!! tip "Getting Help"
    For questions and support, join our [Telegram Support Group](https://t.me/nearaialpha)

## Complete Agent Code

=== "metadata.json"
    ```json
    --8<-- "https://raw.githubusercontent.com/nearai/official-agents/main/near-agent/metadata.json"
    ```

=== "agent.py"
    ```python
    --8<-- "https://raw.githubusercontent.com/nearai/official-agents/main/near-agent/agent.py"
    ```

=== "utils.py"
    ```python
    --8<-- "https://raw.githubusercontent.com/nearai/official-agents/main/near-agent/utils.py"
    ```

=== "state.json"
    ```json
    --8<-- "https://raw.githubusercontent.com/nearai/official-agents/main/near-agent/state.json"
    ```
    
<Center>
[View full example on Github](https://github.com/nearai/official-agents/tree/main/near-agent) 
</Center>