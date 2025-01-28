# (DRAFT) NEAR AI Agent to Agent Protocol

The NEAR AI Agent Protocol is a structured format for sending messages between NEAR AI agents. Usually agents can 
communicate between each other using natural language. For a limited number of cases, a structured format aids in 
communication that may be fulfilled by an agent or a human.

!!! warning "DRAFT"

    This protocol is under active development and discussion. It will change before publication. Only 
    develop against it if you are prepared to change your implementation.


## Compatibility
Agent Protocol messages are sent in Messages on Threads. This format is an extension
of the OpenAI Thread Message format and may or may not be supported by other 
OpenAI compatible libraries. Specifically it introduces a new message content type: `json`. 
We recommend you use the `nearai` client to fetch these messages if you are interacting with them outside the scope of NEAR AI agents.

## Communicating Capabilities
An agent or client that supports the protocol or portions of it communicates this to agents by passing the protocol 
in the `client_capabilities` metadata when invoking the agent. 

In addition, to aid in Agent discovery, compatible agents should list the protocol in the `client_capabilities`
field of their `metadata.json` in the agent registry.

### Client Capabilities format
Communicating full support for v1.
```
client_capabilities: [{
    schema_url: "https://docs.near.ai/v1/agent_protocol.schema.json"
}]
```

Partial support for v1 with enumerated capabilities.
```
client_capabilities: [{
    schema_url: "https://docs.near.ai/v1/agent_protocol.schema.json", 
    supported: ["request_choice", "request_signature"]
}]
```

### List of Client Capabilities in the Agent Protocol
- `request_choice`: The client has special handling for choice messages. 
A UI client might display the choice in a rich UI component. An assistant agent might make a choice on behalf of the user.
- `request_data`: The client can respond to a data request message.
- `request_payment`: The client can respond to a payment request message with a submit payment message.
- `request_signature`: The client can sign transactions or messages for verification.
- `state.json`: The client can operate on a shared state.json file. A UI client might display the state in a rich UI component.

### Additional protocol aspects
These are not communicated in the `client_capabilities` field but are part of the protocol.

 - `action handlers`: Clients can specify that messages are part of the expected flow: making a choice, starting a new product search, etc.
These are communicated to the agent by prefacing a message with <ExpectedAction/>.
This allows agents to do faster processing such as invoking smaller models or programmatically handling the message without an LLM.
 
- `healthcheck`: The client can respond to a healthcheck message. Note that healthcheck usually appears in `metadata.json` listings 
of capabilities and not in capabilities passed to agent invocations.


## Example
[Agent Protocol Example messages](./v1/agent_protocol_example.json)

## Schema
[Agent Protocol JSON schema](./v1/agent_protocol.schema.json)

## Versioning
This protocol follows semantic versioning. 
 * New fields may be added in patch versions.
 * New messages/capabilities may be added in minor versions. 
 * Breaking changes will be introduced in major versions.

# Protocol Details

## Request Choice Message
Confirmation requests may be sent to the user in the form of a choice message.

## Request Data Message

## Request Payment Message

## Request Verification Message

## State.json
To share common state between clients and agents on a thread, the state.json file can be used.
An example is shopping cart state shared between a UI, an assistant agent, and a shopping service agent.
The state is a condensed view of the thread thus far. Distilling conversation state in this manner
and storing it in this known, central location reduces the chances of another LLM pass (which could be in another agent)
reinterpreting the conversation differently between sub-threads of a conversation. It also provides a place for agents to pass structured responses independent of the natural language
response that will be displayed in the conversation.

Sub-threads may be passed portions of this state instead of 
the full conversation.

`intent`: the user's current intent
`shoppingCart`: a list of items in the shopping cart.
`topic`: a file, dataset, or other resource that is the primary focus at this point in the conversation.


## Healthcheck Handling
Whether an agent is properly configured and all its dependent resources are functioning correctly involves checks that may be different for each agent.
Agents can implement a response to the message `/healthcheck`. Agents should respond with a message on the thread they were invoked with. 
This message returned value should start with `OK` if the agent is healthy, `ERROR` if not.