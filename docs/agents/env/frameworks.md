NEAR AI supports several framework configurations, each with its own set of Python packages. Here is an overview of available frameworks, the setting value, and descriptions:

| Framework | Setting | Description |
|-----------|--------|-------------|
| [Minimal](#minimal-framework) | `minimal` | Basic essential packages |
| [Standard](#standard-framework) | `standard` | Default Agent Framework |
| [TypeScript](#typescript-framework) | `ts` | For creating agents with TypeScript  |
| [LangGraph 0.1.4](#langgraph-014-framework) | `langgraph-0-1-4` | For use with [LangGraph](https://github.com/langchain-ai/langgraph) |
| [LangGraph 0.2.26](#langgraph-0226-framework) | `langgraph-0-2-26` | For use with [LangGraph](https://github.com/langchain-ai/langgraph) |
| [AgentKit](#agentkit-framework) | `agentkit` | For use with [Coinbase's Agentkit](https://github.com/coinbase/agentkit) |

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

### LangGraph 0.1.4 Framework

For use with [LangGraph](https://github.com/langchain-ai/langgraph)

```python
--8<-- "aws_runner/frameworks/requirements-langgraph-0-1-4.txt"
```

### LangGraph 0.2.26 Framework

For use with [LangGraph](https://github.com/langchain-ai/langgraph)

```python
--8<-- "aws_runner/frameworks/requirements-langgraph-0-2-26.txt"
```

### AgentKit Framework

For use with [Coinbase's Agentkit](https://github.com/coinbase/agentkit)

```python
--8<-- "aws_runner/frameworks/requirements-agentkit.txt"
```

