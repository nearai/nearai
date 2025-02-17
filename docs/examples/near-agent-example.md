---
title: NEAR AI Agent Example
description: A complete example of a NEAR blockchain agent implementation
---

# NEAR AI Agent Example

!!! note "Source Code"
    The complete NEAR AI Agent Template source code can be found at:
    [github.com/nearai/official-agents/near-agent](https://github.com/nearai/official-agents/near-agent)

## Overview

This example demonstrates how to build an AI agent that interacts with the NEAR blockchain. The agent can perform account operations, token transfers, and staking actions.

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
    Store your private key securely using environment variables:

```python
signer_private_key = globals()['env'].env_vars.get("signer_private_key", None)
```

### Core Agent Logic

```python
async def agent(env: Environment, state: State):
    if not signer_private_key:
        env.add_reply("Add a secret `signer_private_key`...")
```

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

## Related Resources

- [NEAR Protocol Documentation](https://docs.near.org)
- [py-near SDK Reference](https://github.com/near/py-near)
- [NEAR AI Agents Overview](../overview.md)

!!! tip "Getting Help"
    For questions and support, join our [Discord community](https://discord.gg/near)
## Implementation

### Complete Agent Code

```python
{{ gitsnippet('nearai/official-agents', 'near-agent/utils.py') }}
```

