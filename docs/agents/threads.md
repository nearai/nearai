# Threads

Every agent execution happens within a conversation thread, which is isolated from other threads. Threads allow agents to maintain a message history and persist files in time so the user can continue the conversation later.

!!! info

    You can find how agents persist messages and files in the [**Environment: Messages & Files**](./env/messages_files.md) section.

<!-- TODO: add to API docs
Threads follow the OpenAI / LangGraph api standard. `/threads/{thread_id}/messages` will return the messages on the thread.
See the full NEAR AI OpenAPI spec here: [https://api.near.ai/openapi.json](https://api.near.ai/openapi.json) -->

---

## Starting a Thread

If we start an agent without specifying an existing thread, a new thread is created. Let's try this by executing an agent using the interactive mode:

```bash
nearai agent interactive ~/.nearai/registry/<your-account.near>/hello-ai/0.0.1 --local

> Hello, my name is Guille, please remember it

# Example Output:
# ...
# thread_id: thread_43c64803c0a948bc9a8eb8e8

# Assistant: Nice to meet you, Guille! I've made a note of your name, so feel free to ask me anything or start a conversation, and I'll be sure to address you by your name throughout our chat. How's your day going so far, Guillermo?
```

We can see in the output that a new `thread_id` - `thread_43c64803c0a948bc9a8eb8e8` - was created for this conversation.

---

## Resuming a Thread

If we want to resume a conversation thread with an agent, we can specify the thread ID when running the agent:

```bash
nearai agent interactive ~/.nearai/registry/<your-account.near>/hello-ai/0.0.1 --local --thread_id thread_43c64803c0a948bc9a8eb8e8

> What is my name?

# Assistant: Your name is Guille
```

---

## Messages and Files

Agents can access and add messages and files on each thread, learn more about it in the [**Environment: Messages & Files**](./env/messages_files.md) section.