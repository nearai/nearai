# NEAR AI Local Testing Guide

This guide explains how to set up and run the NEAR AI Runner locally. Running the runner locally provides full emulation of the production environment, allowing for proper debugging and fixing of errors that might not be fully reported in the production runner by design.

> [!NOTE]
> **Why Use the Local Runner?**
> By using the local runner, you can:
>   - See all errors from the agent, API, and UI
>   - Run agents directly from your local disk without needing to update versions in the NEAR AI registry
>   - Add necessary packages to local runner frameworks - [contact us](http://t.me/nearaialpha) if to add packages to production runners

---

## Prerequisites

Before starting, ensure you have the following installed:

- [Docker](https://docs.docker.com/engine/install/)
- jq (for processing JSON in shell commands)
- A configured NEAR AI account

---

## Setting Up the Local Runner

1. Clone the repository and navigate to the root directory:
   ```sh
   git clone https://github.com/nearai/nearai.git
   cd nearai
   ```

2. Build the Docker image for the desired framework:

   - **Base framework:**
     ```sh
     docker build -f aws_runner/py_runner/Dockerfile --platform linux/amd64 --build-arg FRAMEWORK=-minimal -t nearai-runner:test .
     ```

3. Start the Docker container and mount all your local agents to the agent registry:
    ```sh
    # Run with datadog support(Must have the datadog environment variables)
    docker run --platform linux/amd64 -p 9009:8080 -v ~/.nearai/registry:/root/.nearai/registry nearai-runner:test

    # Run without datadog support
    docker run --platform linux/amd64 -p 9009:8080 -v ~/.nearai/registry:/root/.nearai/registry -t nearai-runner:test nearai/aws_runner/service.handler
    ```
    This will start the runner on port `9009`.


Alternative: 

Start a pool of three Docker container runners on ports `9009`, `9010`, and `9011`.
```sh
docker-compose -f aws_runner/local_runners/docker-compose.yml up
```
 * aws_runner/local_runners/docker-compose.yml mounts the local agents registry, ~/.nearai/registry, to the container. This allows you to run agents from your local disk. 
 * this pool allows working with multiple agents at once; for example, agents that perform cross agent calls and callbacks.

Notes:
 * On each run, the runner will reload most files mounted from the local registry. For some cases, you may need to restart the local Docker instance to refresh certain file types or file loading patterns.

---

## SingleStore Database

1. Run a local SingleStore Database:

```bash
docker run -d --name singlestoredb-dev \
           -e ROOT_PASSWORD="change-me" \
           --platform linux/amd64 \
           -p 3306:3306 -p 8080:8080 -p 9000:9000 \
           ghcr.io/singlestore-labs/singlestoredb-dev:latest

# Example answer: 74cb1f18d6547373483a7f4aff0e9fe69b44647dca454158dc4673ae5e983db3
```

2. Connect to the docker and create the `hub` database:

```bash
docker exec -it singlestoredb-dev singlestore -p

# Inside the SingleStore shell
CREATE DATABASE hub;
exit;
```

---

## Running the Local Hub
Before starting the hub, make sure to have all the necessary dependencies installed:

```bash
# From the root of the repository
pip install -e ".[hub]"
```

Now, create a `.env` environment file in the **`/hub` folder** - you can use the `hub/.env.example` as a template - and setup the following variables:

```shell
DATABASE_HOST=localhost
DATABASE_USER=root
DATABASE_PASSWORD=change-me
DATABASE_NAME=hub
```

Install `alembic` and apply all migrations using alembic:

```bash
# Install alembic
pip install alembic

# Enter the hub directory and apply migrations
cd hub
alembic upgrade head
```

To use the local runner with the NEAR AI Hub, update the `hub/.env` file:

```
RUNNER_ENVIRONMENT="custom_runner"
CUSTOM_RUNNER_URL=http://localhost:9009/2015-03-31/functions/function/invocations
API_URL=http://host.docker.internal:8081
```

Then, start the local NEAR AI Hub API:

```sh
# within the hub/ directory
fastapi dev app.py --port 8081
```

The Hub API should now be available at **`http://127.0.0.1:8081/`**.

---

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

## Running Agents via the CLI with a Custom Runner
If you have all this running, you will likely want to run agents from the UI. If running from the CLI, there are some
edge cases to consider.

The custom runner authenticates to the Hub API using the `RUNNER_API_KEY` set in the `aws_runner/local_runners/.env` file 
or with the default value in `aws_runner/local_runners/docker-compose.yml`. This should match one of the `TRUSTED_RUNNER_API_KEYS` 
set in `hub/.env`. To run agents from the CLI when your local hub is using a custom runner, pass the `RUNNER_API_KEY` environment variable
with the command, like so:

```sh
RUNNER_API_KEY=custom-local-runner nearai agent interactive <path_to_local_agent> --local
```

This allows agent and runner based features such as agent key value storage and signed completions to work correctly.