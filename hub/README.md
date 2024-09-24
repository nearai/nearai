# NEAR.AI Hub

NEAR.AI Hub allows you to run complex inference based on your needs.

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
