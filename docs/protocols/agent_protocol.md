# NEAR AI Agent to Agent Protocol

The NEAR AI Agent Protocol is a structured format for sending messages between NEAR AI agents. Usually agents can 
communicate between each other using natural language. For a limited number of cases, a structured format aids in 
communication that may be fulfilled by an agent or a human.

## Compatibility
Agent Protocol messages are sent in Messages on Threads. This format is an extension
of the OpenAI Thread Message format and may or may not be supported by other 
OpenAI compatible libraries. We recommend you use the `nearai` client to fetch these
messages if you are interacting with them outside the scope of NEAR AI agents.

## Communicating Capabilities
An agent or client that supports the protocol communicates this to agents by passing the protocol 
in the `client_capabilities` metadata when invoking the agent. 

In addition, to aid in Agent discovery, agents should list the protocol in the `client_capabilities`
field of their `metadata.json` in the agent registry.

### Client Capabilities format
```
client_capabilities: [{
    schema_url: "https://docs.near.ai/v1/agent_protocol.schema.json", 
    supported: ['request_option'] 
}]
```

## Example
[Agent Protocol Example messages](./v1/agent_protocol_example.json)

## Schema
[Agent Protocol JSON schema](./v1/agent_protocol.schema.json)
