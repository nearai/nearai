# Agent Architecture

## Environment

`Environment` is a class which represents a stats of a folder:
 - chat.txt - file with chat history
 - terminal.txt - file with terminal history
 - rest of files that agents can interact with

## Agent

Agents are stored in the Registry under `agents/<agent-alias>/<version>` folder structure.

Agent folder contains:
 - `agent.py` - generic python file that receives `env: Environment`
