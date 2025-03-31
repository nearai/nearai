NEAR AI supports several framework configurations, each with its own set of Python packages. Here is an overview of available frameworks, the setting value, and descriptions:

| Framework | Setting | Description |
|-----------|--------|-------------|
| [Minimal](#minimal-framework) | `minimal` | Basic essential packages - `DEFAULT` |
| [Standard](#standard-framework) | `standard` | More robust Agent Framework|
| [TypeScript](#typescript-framework) | `ts` | For creating agents with TypeScript  |
| [AgentKit](#agentkit-framework) | `agentkit` | For use with [LangChain](https://github.com/langchain-ai/langchain), [LangGraph](https://github.com/langchain-ai/langgraph), or [Coinbase's Agentkit](https://github.com/coinbase/agentkit) |

!!! info "Need a package that is not currently supported?"

    If you have a particular package that is not currently supported, you can reach out to the team to have it added:

      - [Open a PR](https://github.com/nearai/nearai/pulls) -> [(Example)](https://github.com/nearai/nearai/pull/1071)
      - [File an issue](https://github.com/nearai/nearai/issues)
      - [Ask in Telegram](https://t.me/nearaialpha)

## Framework Usage

To use a specific framework, specify it in your agent's `metadata.json`:

```json
{
  "details": {
    "agent": {
      "framework": "standard"  // or "minimal", "ts", "agentkit", etc.
    }
  }
}
```

## Framework Types

Below are up-to-date package support for each framework as defined in NEAR AI's [AWS Runner Frameworks settings](https://github.com/nearai/nearai/tree/main/aws_runner/frameworks).


### Minimal Framework

```python
--8<-- "aws_runner/frameworks/requirements-minimal.txt"
```

### Standard Framework

```python
--8<-- "aws_runner/frameworks/requirements-standard.txt"
```

### TypeScript Framework

For use when creating TypeScript agents.

```python
--8<-- "aws_runner/frameworks/requirements-ts.txt"
```

### AgentKit Framework

For use with [LangChain](https://github.com/langchain-ai/langchain), [LangGraph](https://github.com/langchain-ai/langgraph), or [Coinbase's Agentkit](https://github.com/coinbase/agentkit)

```python
--8<-- "aws_runner/frameworks/requirements-agentkit.txt"
```

