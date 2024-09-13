#!/bin/bash
# This script is run by live bench solver.

if [ $# -eq 0 ]; then
    echo "Error: Please provide a model name as an argument."
    echo "Usage: $0 <model>"
    exit 1
fi

model="$1"

# Remember current directory
CURRENT_DIR=$(pwd)

# Change to LiveBench directory and checkout specific commit
cd ~/.nearai/LiveBench && git checkout e424f7b

# Return to original directory
cd "$CURRENT_DIR"

sudo docker run -it -v ~/.nearai:/.nearai python:3.10 /bin/bash -c "
cd /.nearai/LiveBench && \
pip install -e . && \
cd livebench && \
python show_livebench_results.py --model-list $model
"