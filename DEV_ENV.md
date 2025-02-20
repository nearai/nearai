# Use Python 3.11 slim base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Create a virtual environment
RUN python3 -m venv /venv

# Set the virtual environment path
ENV PATH="/venv/bin:$PATH"

# Copy the application files
COPY . .

# Upgrade pip and install dependencies
RUN pip install --upgrade pip setuptools wheel
RUN pip install -e .
RUN pip install -e .[hub]

# Expose the port the app runs on
EXPOSE 8081

# Command to run the application
CMD ["fastapi", "dev", "app.py", "--port", "8081"]
