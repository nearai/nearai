#!/bin/sh
. .venv/bin/activate # if your virtual environment is elsewhere, change this line
mkdir -p ~/.nearai/registry/user/example_agent/0.0.1
nearai registry metadata_template ~/.nearai/registry/user/example_agent/0.0.1 agent --description="Where would you like to travel?"
cat docs/examples/example_agent.py > ~/.nearai/registry/user/example_agent/0.0.1/agent.py
open ~/.nearai/registry/user/example_agent/0.0.1/metadata.json
open ~/.nearai/registry/user/example_agent/0.0.1/agent.py
echo "Starting example_agent in interactive mode..."
echo "\t type 'exit' to quit."
nearai agent interactive ~/.nearai/registry/user/example_agent/0.0.1 --local