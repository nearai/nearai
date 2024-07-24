#!/bin/bash
set -e

CLI_CMD="/home/setup/.local/bin/nearai"

"$CLI_CMD" version
"$CLI_CMD" supervisor install
"$CLI_CMD" supervisor start
