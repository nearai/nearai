FROM python:3.12-slim-bookworm

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install UV
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    ln -s /root/.local/bin/uv /usr/local/bin/uv && \
    ln -s /root/.local/bin/uvx /usr/local/bin/uvx

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install pip and required packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application
COPY . .

# Expose the port the app runs on
EXPOSE 4001

# Command to run the application
CMD ["python", "server.py"]