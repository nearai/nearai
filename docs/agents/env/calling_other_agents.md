# Calling another agent

Agents can call other agents to interact with them using the [`run_agent`](../../api.md#nearai.agents.environment.Environment.run_agent) method. To call an agent, we need to provide the agent's account, name, and version. Optionally, we can pass a query to the agent.

```python
result = env.run_agent("travel.primitives.near", "trip-organizer", "latest", query="Plan a two-day trip to Buenos Aires", fork_thread=False)
print(result)

# thread_312f2ea5e42742c785218106
```

The result of the `run_agent` method is a string containing the thread ID where the external agent executed.

!!! warning "Shared Environment"
    The agent being called will receive the thread environment, meaning it can access **all the messages and files** from the current conversation. Moreover, the called agent will be able to **add messages and files to the current thread**.

## Thread Fork
The `run_agent` method has an optional `fork_thread` parameter to control whether the called agent should have access to the current thread's messages and files. By default, `fork_thread` is set to `False`.

![alt text](../../assets/agents/call-agent.png)

If we **do fork**, the agent we are calling will work on a copy of the thread, meaning that they have access to all files and messages created so far, but any message or file they create will be part of their own thread.

If we do **not fork** the thread, the called agent will work in the same thread as the current agent, meaning that they have access to all files and messages created so far, and any message or file they create will be part of the current thread.