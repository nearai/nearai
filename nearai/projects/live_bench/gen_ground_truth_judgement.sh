#!/bin/bash
# This script is run by live bench solver.

# Check if a model parameter is provided
if [ $# -eq 0 ]; then
    echo "Please provide a model name as a parameter."
    exit 1
fi

MODEL=$1

# Check if a dataset_ref parameter is provided
if [ $# -eq 1 ]; then
    echo "Please provide a dataset_ref as a parameter."
    exit 1
fi
DATASET_REF=$2

# Truncate DATASET_REF to start from .nearai
DATASET_REF=$(echo $DATASET_REF | sed 's/.*\(\.nearai.*\)/\1/')

# Remember current directory
CURRENT_DIR=$(pwd)

# Clone LiveBench if it doesn't exist
if [ ! -d ~/.nearai/LiveBench ]; then
    git clone https://github.com/LiveBench/LiveBench.git ~/.nearai/LiveBench
fi

# Change to LiveBench directory and checkout specific commit
cd ~/.nearai/LiveBench && git checkout 2fc42c5

# Return to original directory
cd "$CURRENT_DIR"

# Run Docker container
sudo docker run -it -v ~/.nearai:/.nearai pytorch/pytorch:2.0.0-cuda11.7-cudnn8-runtime /bin/bash -c "
    apt-get update && apt-get install -y git
    cd /.nearai/LiveBench
    pip install -e .
    pip install transformers
    pip install accelerate
    pip install nltk
    python -c 'import nltk; nltk.download(\"punkt_tab\")'
    cd livebench
    mkdir -p data/live_bench
    cp -r /$DATASET_REF/* data/live_bench/
    cp -r /.nearai/live_bench_answers/* data/live_bench/
    python gen_ground_truth_judgment.py --question-source jsonl --model-list $MODEL
"