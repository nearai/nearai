# Inference

The `completion` method is used to run a prompt on a specific model, using a specific provider.

<!-- Add link to models and providers -->

If only the prompt is provided, the inference will be run on the model and provider specified in the agent's metadata.

```python
messages = env.list_messages()
result = env.completion(messages)

print("Messages:", messages)
print("Result:", result)
```

??? note "Example Output"
    ```python
    Messages: [{'id': 'msg_1149aa85884b4fe8abc7d859', 'content': 'Hello', 'role': 'user'}]

    Result: Hello! It's nice to meet you. Is there something I can help you with or would you like to chat?
    ```

## Overriding the Default Model

To run the inference on a model different from the default one, you can pass the `MODEL` or `PROVIDER::MODEL` as second argument:

```python
messages = env.list_messages()
result = env.completion([prompt] + messages, "fireworks::qwen2p5-72b-instruct")
```

??? note "Example Output"
    ```python
    Messages: [{'id': 'msg_1149aa85884b4fe8abc7d859', 'content': 'Hello', 'role': 'user'}]

    Result: Hello! How can I assist you today? Is there something specific you'd like to talk about or any questions you have?
    ```

!!! tip

    [`completions`](../../api.md#nearai.agents.environment.Environment.completions): returns the full llm response for more control#


!!! tip "Using Models Locally: LangChain / LangGraph"

    The example agent [langgraph-min-example](https://app.near.ai/agents/flatirons.near/langgraph-min-example/1.0.1/source)
    has metadata that specifies the `langgraph-0-1-4` framework to run on langgraph version 1.4. In addition, the agent.py 
    code contains an adaptor class, `AgentChatModel` that maps LangChain inference operations to `env.completions` calls.
