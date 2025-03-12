# NEAR AI Inference API (OpenAI Compatible)

NEAR AI provides an OpenAI-compatible API for inference, allowing you to easily integrate powerful language models into your applications.

This guide covers the basic inference endpoints and how to use them. For recommended usage of NEAR AI inference in agents explore agent examples below or jump to [Model Match section](#model-match).

Agent examples are available here: [nearai examples](https://github.com/nearai/nearai/tree/main/hub/examples), [nearai_langchain examples](https://github.com/nearai/nearai_langchain/tree/main/examples)

## Getting Started

1. Install all dependencies

   a. using `pip`:

   ```bash
   # Create a virtual environment
   python -m venv nearai_env

   # Activate the virtual environment
   # On Windows:
   # nearai_env\Scripts\activate
   # On macOS and Linux:
   source nearai_env/bin/activate

   # Install the package in editable mode
   pip install -e .
   ```

   b. using uv:

   ```bash
   uv sync --group dev
   ```

2. Set up authentication:

   - Log in to NEAR AI using the CLI: `nearai login`
   - The auth object will be saved in `~/.nearai/config.json`

3. Import the required libraries and set up the client

   ```python
   import openai
   import json
   import os
   import nearai

   hub_url = "https://api.near.ai/v1"

   # Login to NEAR AI Hub using nearai CLI.
   # Read the auth object from ~/.nearai/config.json
   auth = nearai.config.load_config_file()["auth"]
   signature = json.dumps(auth)

   client = openai.OpenAI(base_url=hub_url, api_key=signature)
   ```

## List Models

To list available models, use the `models.list()` method:

```python
models = client.models.list()
print(models)
```

Different providers have different models, and different model formats. For example, fireworks has a format `fireworks::accounts/<namespace>/models/<model_name>`. To get all unique providers, do:

```python
providers = set([model.id.split("::")[0] for model in models])
print(providers)
```

## Create a Chat Completion

To create a chat completion, use the `chat.completions.create()` method. Here's an example:

```python
completion = client.chat.completions.create(
  model="fireworks::accounts/fireworks/models/qwen2p5-72b-instruct",
  messages=[
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello, how are you?"}
  ]
)

print(completion.choices[0].message.content)
```

This will send a request to the specified model with the given messages and return the model's response. The response can be accessed through the `choices` array in the returned object.

## Error Handling

When using the API, it's important to handle potential errors. Here's an example of how to implement basic error handling:

```python
try:
  completion = client.chat.completions.create(
    model="fireworks::accounts/fireworks/models/qwen2p5-72b-instruct",
    messages=[
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Hello, how are you?"}
    ]
  )
  print(completion.choices[0].message.content)
except openai.APIError as e:
  print(f"An API error occurred: {e}")
except Exception as e:
  print(f"An unexpected error occurred: {e}")
```

## Model Match

For agents written in Python, we expect the model name to be given either in `metadata.json` or `env.completion` as `<optional_namespace>/<model_name>`. Examples:
- "llama-v3-70b-instruct"
- "yi-01-ai/yi-large"

"model_provider" may also be optionally specified in `metadata.json`.

Existing provider models are matched against the provided model name, and provider model full path is automatically determined using [`def match_provider_model()`](https://github.com/search?q=repo%3Anearai%2Fnearai%20match_provider_model&type=code) function. This function is executed when:
- `env.completion()` function is called.
- (`nearai_langchain` library) `orchestrator.chat_model` inference is called.

## Additional Features

The NEAR AI Inference API also supports other features such as:

1. Streaming responses
2. Function calling
3. Custom parameters (temperature, max_tokens, etc.)

For more information on these features, please refer to the full API documentation.

## Conclusion

This guide covers the basics of using the NEAR AI Inference API. By following these steps, you should be able to authenticate, list models, and create chat completions. For more advanced usage and detailed information, please refer to the complete API documentation or explore the provided examples.
