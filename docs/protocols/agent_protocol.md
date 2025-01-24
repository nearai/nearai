# NEAR AI Agent to Agent Protocol

The NEAR AI Agent Protocol is a structured format for sending messages between NEAR AI agents. Usually agents can 
communicate between each other using natural language. For a limited number of cases, a structured format aids in 
communication that may be fulfilled by an agent or a human.

## Compatibility
Agent Protocol messages are sent in Messages on Threads. This format is an extension
of the OpenAI Thread Message format and may or may not be supported by other 
OpenAI compatible libraries. We recommend you use the `nearai` client to fetch these
messages if you are interacting with them outside the scope of NEAR AI agents.

