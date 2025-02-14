# Dependencies
brew install jq
python3 -m pip install nearai
pip install "fastapi[standard]"

# Build runner
docker build -f aws_runner/py_runner/Dockerfile --platform linux/amd64 --build-arg FRAMEWORK=-base -t nearai-runner:test .

# Run Runner
docker run --platform linux/amd64 -p 9009:8080 -v ~/.nearai/registry:/root/.nearai/registry nearai-runner:test

# Database

docker run -d --name singlestoredb-dev \
           -e ROOT_PASSWORD="change-me" \
           --platform linux/amd64 \
           -p 3306:3306 -p 8080:8080 -p 9000:9000 \
           ghcr.io/singlestore-labs/singlestoredb-dev:latest



# Run Hub

## Env Variables
DATABASE_HOST=localhost
DATABASE_USER=root
DATABASE_PASSWORD=change-me
DATABASE_NAME=hub
RUNNER_ENVIRONMENT="custom_runner"
CUSTOM_RUNNER_URL=http://localhost:9009/2015-03-31/functions/function/invocations
API_URL=http://host.docker.internal:8081

## Run Hub migrations:
### Install alembic
pip install alembic
### Apply migrations
alembic upgrade head

## Run Hub

brew install python@3.11
pip install virtualenv  
virtualenv -p /opt/homebrew/bin/python3.11 myenv
source myenv/bin/activate
pip install -e .  
pip install -e .\[hub\]

fastapi dev app.py --port 8081


