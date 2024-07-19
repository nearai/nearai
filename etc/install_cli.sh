#!/bin/bash
set -e

NEARAI_DATA=/home/setup/.nearai
CLI_REPO="$NEARAI_DATA/nearai"
CLI_CMD="/home/setup/.local/bin/nearai"

mkdir -p $NEARAI_DATA

# Download nearai
if [ ! -d "$CLI_REPO" ]; then
    git clone git@github.com:nearai/nearai.git $CLI_REPO
fi

# Update latest version
cd $CLI_REPO
git checkout main
git pull

python3 -m pip install --upgrade pip
python3 -m pip install -e .
