# Running Agents Based on Events from the NEAR Blockchain

## Overview
The NEAR AI HUB monitors the latest blocks from the NEAR blockchain and can trigger agents when it detects `EVENT_JSON` entries following the `nearai` standard in transactions.

### Example of an Event Log Entry
```json
{
  "standard": "nearai",
  "version": "0.1.0",
  "event": "run_agent",
  "data": [
    {
      "message": "Hello from NEAR Blockchain",
      "agent": "user.near/agent-name/latest",
      "max_iterations": null,
      "env_vars": null,
      "signer_id": "account.near",
      "referral_id": null,
      "request_id": null,
      "amount": "0"
    }
  ]
}
```

[Example Transaction](https://nearblocks.io/txns/897d24mgHePaVjojMWc3w3hmBgFS1z4VLkujHLTxGdpp#execution).


When such an event is detected, the agent specified in the `agent` field (e.g., `user.near/agent-name/latest`) will be automatically triggered. The agent will receive a JSON string containing the following object as its input:

```json
{
  "event": "run_agent",
  "message": "...",
  "receipt_id": "...",
  // Other fields from the `data` object in the logs.
}
```

To allow your agent to be invoked in this way, add a function that parses the incoming user message as a JSON string. If the required values for `event` and `message` are present, it should take the appropriate actions. The agent is not required to trust the data sent by the NEAR AI HUB and can independently verify the blockchain by reading the necessary block based on the `receipt_id`.


