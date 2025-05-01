# Agent Streaming
## Table of Contents

- [Streaming completions in an agent result in agent streaming](#streaming-completions-in-an-agent-result-in-agent-streaming)
- [UI app.near.ai](#ui-appnearai)
- [CLI](#cli)
- [Agent settings](#agent-settings)
- [Agent usage](#agent-usage)
- [Multiple streaming invocations!](#multiple-streaming-invocations)
- [API Usage](#api-usage)
- [Full File examples](#full-file-examples)
  - [Full agent example](#full-agent-example)
  - [Full metadata file with show_streaming_message setting](#full-metadata-file-with-show_streaming_message-setting)

## Streaming completions in an agent result in agent streaming
When an Agent streams completions by passing `stream=True`, those completion chunks are streamed back to the agent.

```python
    result = self.env.completion([prompt] + messages, stream=True) # stream the completions!
    self.env.add_reply(result) # write the full message to the thread as normal
```
The chunks are also persisted temporarily on the hub and made available to clients through 
the `/threads/{thread_id}/stream/{run_id}` endpoint.

## UI app.near.ai
Agent streaming is automatically handled by the UI.
An indicator of chunks received is shown to the user.

![Streaming screenshot.png](../assets/Streaming%20screenshot.png)

### CLI
Similarly, the CLI shows streaming chunks as they are received. It only has one display mode (show the chunks) and does not use the `show_streaming_message` setting detailed in the next section.
You can switch between CLI streaming and message modes by using the `--stream` flag. `--stream=False` will show final messages only.

### Agent settings
To show the tokens as they are received, set the agent metadata `"show_streaming_message": true`
inside details->agents. A full file example can be found at the end of this page.

If your agent has tool calls, inter-agent messaging, makes decisions before deciding output, or otherwise produces non-user facing completions,
you may want to set `"show_streaming_message": false` to avoid showing the user partial messages.

However, this streaming text will be replaced as soon as the next message comes in. For completions that 
combine user facing text and non-user facing text, some apps may want to briefly show the raw streaming text, quickly replacing 
it with the final message. This is a design decision for the app to make.

`show_streaming_message` defaults to `true`


## Agent usage
Within the agent the completion function returns a StreamHandler object when stream=True. 
This can be iterated over or passed to streaming libraries that accept a StreamHandler.
```python
    resp_stream = self.env.completion([prompt] + messages, stream=True)

    for event in resp_stream:
        for _idx, chunk in enumerate(resp_stream):
            c = json.dumps(chunk.model_dump())
            print(c)
            # do something with the chunk

    self.env.add_reply(resp_stream) # write the full message to the thread
```
Use of the /thread/

## Multiple streaming invocations!
A single agent run can contain multiple streaming completion calls!

In this example two different personas are passed the same conversation history.
```python
        prompt = {"role": "system", "content": "respond as though you were Socrates"}
        messages = self.env.list_messages()

        result = self.env.completion([prompt] + messages, stream=True)
        self.env.add_reply(result)

        prompt2 = {"role": "system", "content": "Now, respond as though you were Plato"}
        result2 = self.env.completion([prompt2] + messages, stream=True)
        self.env.add_reply(result2)
```

## API Usage
Calls to the `/threads/{thread_id}/stream/{run_id}` endpoint return an SSE EventStream of deltas and thread events.
These events are compatible with OpenAI Thread streaming events, https://platform.openai.com/docs/api-reference/assistants-streaming/events

### Javascript example
A React client might handle streaming as follows.

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


## Full File examples

### Full agent example
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

        self.env.request_user_input()

if globals().get('env', None):
    agent = Agent(globals().get('env'))
    agent.run()
```




### Full metadata file with show_streaming_message setting
```
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
        "max_iterations": 1,
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