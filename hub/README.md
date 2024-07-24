# NEAR.AI Hub

NEAR.AI Hub allows you to run complex inference based on your needs.

It supports multiple providers and can be easily extended to support more. Supported inference providers: [Link](./api/v1/completions.py#L12)

## Server

### Database setup

- Make sure you have a MySql database running. Example using docker:

```bash
docker run --name mysql -d \
    -p 3306:3306 \
    -e MYSQL_ROOT_PASSWORD=change-me \
    --restart unless-stopped \
    mysql:latest
```

- Apply migrations available here: [link](./migrations/20240604133844_init.sql).
  - Apply migrations using: `make apply-migrations` or `make docker-apply-migrations`, depending on your setup.

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

- Move to `demo` directory:

```bash
cd demo
```

- Install the dependencies:

```bash
npm install
```

- Copy the `.env.example` file to `.env` and update the values as needed.

```bash
cp .env.example .env
```

- Start the next app in development mode:

```bash
npm run dev
```
