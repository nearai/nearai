#!/bin/sh
mkdir -p ~/.nearai/registry/example_agent
nearai registry metadata_template ~/.nearai/registry/example_agent
cat docs/example_agent.py.txt > ~/.nearai/registry/example_agent/agent.py
open ~/.nearai/registry/example_agent/metadata.json
open ~/.nearai/registry/example_agent/agent.py
echo "Starting example_agent in interactive mode..."
echo "\t type 'exit' to quit."
echo "Agent: Where would you like to travel?"
nearai agent interactive example_agent /tmp/example_agent_run_1 --local