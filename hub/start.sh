#!/usr/bin/env bash
set -e

## check for connection to db
max_attempts=60
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if timeout 1 bash -c "</dev/tcp/${DATABASE_HOST}/3306" >/dev/null 2>&1; then
        echo "Database connection successful"
        break
    else
        echo "Waiting for database connection... (Attempt $((attempt+1))/$max_attempts)"
        attempt=$((attempt+1))
        sleep 1
    fi
done

if [ $attempt -eq $max_attempts ]; then
    echo "Failed to connect to the database after $max_attempts attempts. Exiting."
    exit 1
fi

sleep 3
alembic upgrade head
fastapi run app.py --port 8081