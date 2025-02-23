# NEAR AI Local Testing Guide

This guide explains how to set up and run the NEAR AI Runner locally. Running the runner locally provides full emulation of the production environment, allowing for proper debugging and fixing of errors that might not be fully reported in the production runner by design.

## Why Use the Local Runner?

By using the local runner, you can:

- See all errors from the agent, API, and UI.

- Run agents directly from your local disk without needing to update versions in the NEAR AI registry.

- Add necessary packages to local runner frameworks ([contact us](http://t.me/nearaialpha) if you need these packages added to the production runners later).

## Prerequisites

Before starting, ensure you have the following installed:

- Docker
- jq (for processing JSON in shell commands)
- A configured NEAR AI account

## Setting Up the Local Runner

1. Clone the repository and navigate to the root directory:
   ```sh
   git clone https://github.com/nearai/nearai.git
   cd nearai
   ```

2. Build the Docker image for the desired framework:

   - **Base framework:**
     ```sh
     docker build -f aws_runner/Dockerfile --platform linux/amd64 --build-arg FRAMEWORK=-base -t nearai-runner:test .
     ```

3. Start the Docker container and mount all your local agents to agent registry:
   ```sh
   docker run --platform linux/amd64 -p 9009:8080 -v ~/.nearai/registry:/root/.nearai/registry nearai-runner:test
   ```
   This will start the runner on port `9009`.

    Note: Sometimes, you may need to restart the local Docker instance to refresh files mounted from the local agents registry.

4. Run a local SingleStore Database:

```bash
docker run -d --name singlestoredb-dev \
           -e ROOT_PASSWORD="change-me" \
           --platform linux/amd64 \
           -p 3306:3306 -p 8080:8080 -p 9000:9000 \
           ghcr.io/singlestore-labs/singlestoredb-dev:latest
```

Set database environment variables in the `hub/.env` file:

```shell
DATABASE_HOST=localhost
DATABASE_USER=root
DATABASE_PASSWORD=change-me
DATABASE_NAME=hub
```

Apply all migrations using alembic:

```bash
# Install alembic
pip install alembic
# Apply migrations
alembic upgrade head
```

## Running the Local Hub

To use the local runner with the NEAR AI Hub, update the `hub/.env` file:

```
RUNNER_ENVIRONMENT="custom_runner"
CUSTOM_RUNNER_URL=http://localhost:9009/2015-03-31/functions/function/invocations
API_URL=http://host.docker.internal:8081
```
Then, start the local NEAR AI Hub API:
```sh
cd hub
fastapi dev app.py --port 8081
```

## Running the Local Hub UI

1. Navigate to the Hub UI directory:
   ```sh
   cd hub/demo
   ```

2. Update the `hub/demo/.env` file to use the local runner:
   ```
   ROUTER_URL=http://127.0.0.1:8081/v1
   DATA_SOURCE="local_files"
   ```

3. Start the UI:
   ```sh
   npm install
   npm run dev
   ```

The UI should now be available in your browser at `http://localhost:3000`. It will display all your local agents. Run it using the local runner by clicking the "Run" Tab and sending messages to the agent. Don't forget to recreate secrets locally if needed.

## Viewing Logs

- **Container Logs:** Run the following command to view logs from the local runner:
  ```sh
  docker logs -f nearai-runner:test
  ```

- **Local Hub Logs:** Check the logs from the NEAR AI Hub API and Local UI

With this setup, you can fully emulate the production runner environment and debug AI agents efficiently.