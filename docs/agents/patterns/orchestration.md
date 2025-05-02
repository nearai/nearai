# Orchestrating multiple agent

NEAR AI provides flexible architecture for orchestrating multiple agents to work together effectively.

## One Agent - One Trust Boundary

Usually, a swarm of multiple agent roles can be all orchestrated within a single deployed NEAR AI agent. If your organization is the author of all the agents, combining these roles into a single agent is the most straightforward and often recommended approach which keeps things simple, efficient, and within one trust boundary.

**Examples:**

 * [common-tool-library-agent](https://github.com/nearai/official-agents/tree/main/common-tool-library) - contains 
    over a hundred prompts for tackling specific problems
 * [langchain-reflection-agent](https://app.near.ai/agents/snpark.near/example_langgraph_reflection_agent/latest/source) - 
    contains separate code generation and reviews sub-agents that hand off work to each other

To track turns or which sub-agent to invoke there are two common patterns:

 * **Router** - the initial agent logic reviews the thread messages and decides which sub-agent to call.
 * **State file** - a file is written to the thread that contains the current programmatic state of the conversation. 
    The agent reads this file to determine what to do next. See [messages_files.md](../env/messages_files.md).

## Agent to Agent - Multiple trust boundaries

Agents can call other agents to interact with them using the [`run_agent`](../../api.md#nearai.shared.inference_client.InferenceClient.run_agent) method.
This can be on the same thread or a sub-thread. This introduces multiple trust boundaries which should be considered before implementation.

For more information on this, see [Agent to Agent Communication](./agent_to_agent.md).

## API integration

External applications can call one or more NEAR AI Agents using the NEAR AI Assistants API. For more on this, see [Integrating Agents](../integration.md).
