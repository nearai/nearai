# Environment Variables

When working with agents, managing configuration parameters through environment variables can provide a flexible way to adjust settings without altering the underlying code. This approach is particularly useful when dealing with sensitive information or configuration that needs to be customized without modifying the agent's codebase.

---

## Storing Environment Variables

Environment variables can be stored in a metadata.json file. Here’s an example of how to structure this file:

```json
{
  "details": {
    "env_vars": {
      "id": "id_from_env",
      "key": "key_from_env"
    }
  }
}
```

---

## Accessing Environment Variables in Code

In your agent’s code, you can access these environment variables using Python’s os module or by accessing the env_vars dictionary directly.

To retrieve an environment variable in the agent code:

```python
# Using os.environ
import os
value = os.environ.get('VARIABLE_NAME', None)

# Or using globals()
value = globals()['env'].env_vars.get('VARIABLE_NAME')
```

This allows users to fork the agent, modify the environment variables in `metadata.json`, and achieve the desired behavior without changing the code itself.

---

## Running the agent with Environment Variables

You can also pass environment variables directly when launching the agent. This can be useful for overriding or extending the variables defined in `metadata.json` and handling Sensitive Information: If your agent needs to interact with APIs or services that require secret keys or credentials, you can pass these as environment variables instead of hardcoding them. This ensures that sensitive information is not exposed in publicly accessible code.

To run the agent with environment variables, use the following command:

```shell
nearai agent interactive user.near/agent/1 --local --env_vars='{"foo":"bar"}'
```

####  Example

Consider an agent `zavodil.near/test-env-agent/1` that has configurable environment variables.

