#!/bin/sh
pip install nearai
nearai login
nearai agent create -name example_agent --description "Descriptions help users and other agents identify when your agent is useful."

echo "\nStarting example_agent in interactive mode..."
echo "\t type 'exit' to quit."
nearai agent interactive ~/.nearai/registry/YOUR_ACCOUNT_NAME/example_agent/0.0.1 --local