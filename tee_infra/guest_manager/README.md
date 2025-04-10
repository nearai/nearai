# Guest Manager

A service for managing CVM (Confidential Virtual Machine) instances.

## Building with Docker

This project uses Docker BuildKit for reproducible builds across different platforms.

### Prerequisites

- Docker 19.03 or later (with BuildKit support)
- Docker Compose (optional, for compose-based builds)
- Bash shell

### Build Script

The `build.sh` script in the root directory provides a convenient way to build the Docker image:

```bash
# Basic build
./build.sh

# Build with a specific tag
./build.sh --tag v1.0.0

# Build for a specific platform
./build.sh --platform linux/arm64

# Build using Docker Compose
./build.sh --mode compose

# Save the image to a tarball after building
./build.sh --save

# Show help
./build.sh --help
```

### Manual Build

If you prefer to build manually:

```bash
# Enable BuildKit
export DOCKER_BUILDKIT=1

# Build the image
docker build \
  -f tee_infra/guest_manager/Dockerfile \
  -t guest_manager:latest \
  --build-arg BUILD_TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ") \
  .
```

### Using Docker Compose

```bash
# Enable BuildKit for Compose
export COMPOSE_DOCKER_CLI_BUILD=1
export DOCKER_BUILDKIT=1

# Build and run
cd tee_infra/guest_manager
docker-compose build
docker-compose up -d
```

## Running the Service

The guest_manager service requires access to the Docker socket to manage containers:

```bash
docker run -p 3000:3000 -v /var/run/docker.sock:/var/run/docker.sock guest_manager:latest
```

## API Endpoints

- `GET /health` - Health check endpoint
- `POST /assign_cvm` - Assign a CVM to a run

## Environment Variables

- `RUST_LOG` - Log level (default: info)

## Cross-Platform Builds

The build system supports building for different platforms:

- linux/amd64 (default)
- linux/arm64
- darwin/amd64 (macOS Intel)
- darwin/arm64 (macOS Apple Silicon)

Use the `--platform` flag with the build script to specify the target platform. 