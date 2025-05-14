# Agent Streaming

## What is Agent Streaming?

Agent streaming enables output from your agent in a continuous, incremental stream, rather than waiting for a complete one-time response. This improves the user experience by providing immediate feedback and preventing long wait times especially for complex tasks such as multi-step reasoning, data analysis, or tool-based interactions.

## Getting Started

To use agent streaming, first implement streaming completions in your agent's code by passing `stream=True` to your `completion` function:

```python
    result = self.env.completion([prompt] + messages, stream=True)
```

_( See [streaming completions](#streaming-completions) for more details.)_

Once complete, you can now view these streams in the UI or CLI, each having their own unique way to enable.

#### Enable UI Streaming

To enable agent streaming in the UI, add `"show_streaming_message": true` to the `agent` details within your agent's [`metadata.json` file](./quickstart.md/#metadatajson):

```json
  "details": {
    "agent": {
      "show_streaming_message": true
    }
  }
```

See [full example below](#__tabbed_1_2)

The UI automatically receives the same stream as the agent. A counter of deltas received and optionally the stream of text itself are shown to the user.

![Streaming screenshot.png](../assets/Streaming%20screenshot.png)

!!! note
    If your agent produces intermediate, non-user-facing completions (e.g., during tool calls or complex reasoning steps), you might set `"show_streaming_message": false` to prevent partial or internal messages from being displayed directly to the user in the UI.

    It's also important to note that the streaming text is immediately replaced upon the next message, so some applications might still prefer `true` even with intermediate steps.

#### Enable CLI Streaming

To enable agent streaming in the CLI use the `--stream=True` flag when running `nearai agent interactive`.

- This method only has display mode (show each chunk of text) and only shows the final messages.
- Use this flag each time you run an agent as it does not use the `show_streaming_message` setting from your `metadata.json`

!!! note
    As with UI streaming, you must first implement [streaming completions](#streaming-completions) in your agent's code _before_ using this command. When working with different agent types (streaming & non-streaming) the following behavior is expected:

    * An agent that **does not** stream completions that is run in `nearai agent interactive` mode with `--stream=True` will show **no output**.
    * An agent that **does** stream completions will by default show the final message only. When passed `--stream=True` it will show the text as it is received.

## Streaming Completions

To stream completion chunks to your agent, pass `stream=True` when using the `completion` function:

Example:

```python
    result = self.env.completion([prompt] + messages, stream=True) # stream the completions!
    self.env.add_reply(result) # write the full message to the thread as normal
```

These chunks are also persisted temporarily on the Agent Cloud (Hub) and made available to clients through 
the `/threads/{thread_id}/stream/{run_id}` endpoint.

* Chunk: One or more tokens streamed from the LLM to the agent.
* Delta: An SSE event that contains a chunk, streamed to clients.

[See full example below for more](#__tabbed_1_1)

### Agent Usage

Within the agent the completion function returns a `StreamHandler` object when `stream=True`. 
This can be iterated over or passed to streaming libraries that accept a `StreamHandler`.

```python
    response_stream = self.env.completion([prompt] + messages, stream=True)

    for event in response_stream:
        for _idx, chunk in enumerate(response_stream):
            c = json.dumps(chunk.model_dump())
            print(c)
            # do something with the chunk
            
            # if part of a chain of async calls you could yield the chunk or evaluate or modify it and yield
            # yield chunk
    self.env.add_reply(response_stream) # write the full message to the thread
```

[See full example below for more](#__tabbed_1_1)

### Multiple Streaming Invocations

A single agent run can contain multiple streaming completion calls!

Here is an example where two different personas are passed the same conversation history:

```python
        prompt = {"role": "system", "content": "respond as though you were Socrates"}
        messages = self.env.list_messages()

        result = self.env.completion([prompt] + messages, stream=True)
        self.env.add_reply(result)

        prompt2 = {"role": "system", "content": "Now, respond as though you were Plato"}
        result2 = self.env.completion([prompt2] + messages, stream=True)
        self.env.add_reply(result2)
```

 [See full example below for more](#__tabbed_1_1)

## Streaming API

Calls to the `/threads/{thread_id}/stream/{run_id}` endpoint return an SSE EventStream of deltas and thread events.
These events are compatible with OpenAI Thread streaming events, https://platform.openai.com/docs/api-reference/assistants-streaming/events.

Here is an example of how a React client might use this API endpoint:

```javascript
  const startStreaming = (threadId: string, runId: string) => {
    if (!threadId) return;
    if (!runId) return;

    setIsStreaming(true);

    const eventSource = new EventSource(
      `/api/v1/threads/${threadId}/stream/${runId}`,
    );

    eventSource.addEventListener('message', (event) => {
      const data = JSON.parse(event.data);
      const eventType = data.event;
      
      switch (eventType) {
        case 'thread.message.delta':
          if (!data?.data?.delta?.content) return;
          const content = data.data.delta.content;
          if (content.length === 0 || !content[0]?.text?.value) return;
          const latestChunk = data.data.delta.content[0].text.value;
          setStreamingText((prevText) => prevText + latestChunk);
          setStreamingTextLatestChunk(latestChunk);

          // Force React to rerender immediately rather than batching
          setTimeout(() => {}, 0);
          break;

        case 'thread.message.completed':
          setStreamingText('');
          setStreamingTextLatestChunk('');
          break;
        case 'thread.run.completed':
        case 'thread.run.error':
        case 'thread.run.canceled':
        case 'thread.run.expired':
        case 'thread.run.requires_action':
          stopStreaming(eventSource);
          break;
      }
    });

    eventSource.onerror = (error) => {
      console.log('SSE error:', error);
      eventSource.close();
      setIsStreaming(false);
    };

    setStream(eventSource);

    return () => {
      eventSource.close();
    };
  };
```

## Advanced Streaming / FAQs

 * Child threads do not currently support streaming thus invoking another agent on a child thread will not stream.
 * Agent initiated Deltas
     * Writing delta events from the agent to the agent stream is not currently supported.
 * Tools: 
     * There is not currently any special handling of tool calls.
     * Tool call responses vary between providers and models, thus some models will have tool calls in the main response
        and others will not.
     * Depending on your use case you may want to separate tool calls from the main response rather than requesting 
        both in the same completion call.

## Full Agent Streaming Example

=== "agent.py"

    ```python
    from nearai.agents.environment import Environment

    class Agent:
        def __init__(self, env: Environment):
            self.env = env

        def run(self):
            prompt = {"role": "system", "content": "respond as though you were Socrates"}
            messages = self.env.list_messages()

            # Pass stream=True to enable streaming of deltas
            # They will then show automatically in the UI or can be fetched at /threads/{thread_id}/stream/{run_id}
            result = self.env.completion([prompt] + messages, stream=True)
            self.env.add_reply(result)

            prompt2 = {"role": "system", "content": "Now, respond as though you were Plato"}
            result2 = self.env.completion([prompt2] + messages, stream=True)
            self.env.add_reply(result2)

    if globals().get('env', None):
        agent = Agent(globals().get('env'))
        agent.run()
    ```

=== "metadata.json"

      ```json
        "name": "streaming-example",
        "version": "0.0.3",
        "category": "agent",
        "description": "Demonstrates streaming agent runs.",
        "tags": ["streaming"],
        "details": {
          "display_name": "Streaming Example",
          "icon": "https://static.thenounproject.com/png/1677760-200.png",
          "agent": {
            "show_streaming_message": true,
            "welcome": {
              "title": "Example of streaming agent runs",
              "description": "I respond as Socrates then as Plato."
            },
            "defaults": {
              "model": "llama-v3p3-70b-instruct",
              "model_max_tokens": 4000,
              "model_provider": "fireworks"
            }
          },
          "capabilities": []
        },
        "show_entry": true
      }
      ```