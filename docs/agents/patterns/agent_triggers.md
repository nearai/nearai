# Agent Triggers

Agents can be triggered by having them listen to a named event source.

# Twitter (X)
NearAI maintains a read-only Twitter interface that can be used to trigger agents under certain conditions. 

# The x_mentions event source
The `x_mentions` event source produces an event when a configured account is mentioned.

To have an agent listen for mentions, create trigger metadata in the agent's metadata.json file as in the example below.

To trigger an agent, mention the X account configured in the metadata.json. The agent will be invoked.

```json
{
  "name": "near-secret-agent",
  "version": "0.0.1",
  "description": "An example agent that responds to Twitter mentions",
  "category": "agent",
  "tags": ["twitter"],
  "details": {
    "agent": {
      "welcome": {
        "title": "No chat interface",
        "description": "To use tweet a message and mention @nearsecretagent."
      },
      "defaults": {
        "max_iterations": 1,
        "model": "llama-v3p2-3b-instruct",
        "model_provider": "fireworks",
        "model_temperature": 0.0,
        "model_max_tokens": 1000
      }
    },
    "triggers": {
      "events" : {
        "x_mentions": ["@nearsecretagent"]
      }
    }
  },
  "show_entry": true
}
```

## Posting to Twitter (X)

To allow your agent to post to X you will need your own developer api key. Free X developer accounts have low read limits but fairly high write limits.

NearAI Runners include the `tweepy` library, which supports several ways to authenticate with X https://docs.tweepy.org/en/stable/authentication.html

The example agent https://app.near.ai/agents/flatirons.near/near-secret-agent/latest/source uses 3 legged Oauth to 
authorize an X account other than the developer account to post through the api as described here in the [twitter docs](https://developer.x.com/en/docs/authentication/oauth-1-0a/api-key-and-secret).
To accomplish this it has four secrets set on the agent: X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET, X_CONSUMER_KEY, X_CONSUMER_SECRET.

