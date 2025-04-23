FROM node:18-slim

WORKDIR /app

# Install system dependencies with retry mechanism
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy package files first to leverage Docker cache
COPY package.json ./
RUN npm install

# Copy the rest of the application
COPY . .

# Build TypeScript
RUN npx tsc

# Expose the port the app runs on
EXPOSE 4000

# Command to run the application
CMD ["node", "dist/server.js"]