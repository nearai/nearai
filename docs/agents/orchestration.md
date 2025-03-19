# Orchestrating multiple agents

NEAR AI supports several strategies for orchestrating multiple agents.

## One trust boundary, one Agent
Usually, a swarm of multiple agent roles can be orchestrated all within a single deployed NEAR AI agent. If your organization is the
author of all the agents, keep things simple and efficient by keeping them within a single named agent in the registry. This 
keeps everything within one trust boundary, avoids dealing with multiple agent versions, and simplifies the orchestration logic.

Examples: 

 * the [common-tool-library](https://github.com/nearai/official-agents/tree/main/common-tool-library) agent contains 
    hundreds of prompts for tackling specific problems.
 * the [langchain-reflection-agent](https://app.near.ai/agents/snpark.near/example_langgraph_reflection_agent/latest/source)
    contains separate code generation and review sub-agents that hand off work to each other.

To track turns or which sub-agent to invoke there are two common patterns.

 * Router, the initial agent logic reviews the thread messages and decides which sub-agent to call.
 * State file,  a file is written to the thread that contains the current programmatic state of the conversation. 
    The agent reads this file to determine what to do next. See [messages_files.md](env/messages_files.md).

## Agent-to-Agent Communication, multiple trust boundaries

Agents can call other agents to interact with them using the [`run_agent`](../api.md#nearai.agents.environment.Environment.run_agent) method.
This can be on the same thread or a sub-thread.

## API integration

External applications can call one or more NEAR AI Agents using the NEAR AI Assistants API. [overview.md](../integration/overview.md)
