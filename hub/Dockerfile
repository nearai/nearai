FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/* \
    && curl -sSL https://install.python-poetry.org | python3 -

ENV PATH="/root/.local/bin:$PATH"

COPY pyproject.toml poetry.lock* /app/

RUN poetry install --no-root

COPY . /app

RUN echo '#!/bin/bash\n\
cd hub\n\
source /app/.docker-env/bin/activate\n\
fastapi dev app.py --port 8081\n\
' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh


CMD ["/app/entrypoint.sh"]
