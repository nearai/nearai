FROM python:3.11

# Install dependencies for Rust and Cargo
RUN apt-get update && apt-get install -y curl build-essential

# Install Rust and Cargo, and make them available in PATH
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container
COPY . .

# Create a Python virtual environment
RUN python -m venv /opt/venv

# Upgrade pip to the latest version
RUN /opt/venv/bin/python -m pip install --upgrade pip

# Install maturin and check its version
RUN /opt/venv/bin/python -m pip install maturin && /opt/venv/bin/maturin --version

# Install the Python package in editable mode
RUN /opt/venv/bin/python -m pip install -e .
