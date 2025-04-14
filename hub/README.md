# NEAR AI Hub

NEAR AI Hub allows you to run complex inference based on your needs.

It supports multiple providers and can be easily extended to support more. Supported inference providers: [Link](./api/v1/completions.py#L12)

## Server

### Database setup

-   Run a SingleStore Database. [Example using docker](https://github.com/singlestore-labs/singlestoredb-dev-image):

```bash
docker run -d --name singlestoredb-dev \
           -e ROOT_PASSWORD="change-me" \
           --platform linux/amd64 \
           -p 3306:3306 -p 8080:8080 -p 9000:9000 \
           ghcr.io/singlestore-labs/singlestoredb-dev:latest
```

-   Copy .env.example to .env and update DATABASE\_\* values as needed.
-   Apply all migrations using [alembic](https://alembic.sqlalchemy.org/en/latest/).

```bash
# Install alembic
pip install alembic

# Apply migrations
alembic upgrade head
```

### Python server setup

Copy example environment variables file and **make sure the values are correct**:

```bash
cp .env.example .env
```

Create venv and install the dependencies:

```bash
python -m venv venv
source venv/bin/activate
pip install -e .
pip install -e .[hub]  # on MacOS use `pip install -e .\[hub\]`
```

Start the dev server with:

```
fastapi dev app.py --port 8081
```

Start production server with:

```
fastapi run app.py --port 8081
```

## Frontend

### Setup

-   Move to `demo` directory:

```bash
cd demo
```

-   Install the dependencies:

```bash
npm install
```

-   Copy the `.env.example` file to `.env` and update the values as needed.

```bash
cp .env.example .env
```

-   If running only Frontend, update the Router URL in `.env` to
```bash
ROUTER_URL=https://api.near.ai/v1
```

-   Start the next app in development mode:

```bash
npm run dev
```

## Local Hub Features
To enable the feature for "[Running Agents Based on Events from the NEAR Blockchain](/docs/near_events.md)," follow these steps:

1. Set `READ_NEAR_EVENTS=True` in the `.env` file.
2. Log in to NEAR AI by running [NEAR Login](/docs/login.md):

   During this process, you will be prompted to sign with a NEAR account created for your hub. This signature will be used to trigger agents.

## How to Sign HUB completions

Set up `hub/.env`:
- Define `HUB_PRIVATE_KEY` as the master private key to derive agents' private keys.
- set `TRUSTED_RUNNER_API_KEYS` and list the API keys of all runners authorized to generate signed completions.

Set up `RUNNER_API_KEY`:
- If you are running Docker locally, pass `RUNNER_API_KEY` as runtime parameter (`docker run -e RUNNER_API_KEY=...`)
- If you are using AWS Lambda, navigate to Lambda -> Functions -> Configuration -> Environment variables  and add a new key named `RUNNER_API_KEY`.

Once this setup is complete, agents will be able to receive signatures from the `env.signed_completion` method.

**Why This Is Important**

If any runner is allowed to request signatures from the Hub without proper restrictions, it could send modified agent code and still receive valid signatures. This compromises the integrity of the signed completions and opens the system to potential security risks.

When TEE runners are implemented, this security measure can be simplified.

Note: The `RUNNER_API_KEY` will not be accessible within the agent environment.