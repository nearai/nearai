#!/bin/bash
set -euo pipefail

# Determine script and project root directories.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

IMAGE_NAME="guest_manager"
IMAGE_TAG="latest"
DOCKERFILE_PATH="${SCRIPT_DIR}/Dockerfile"

# Parse command line arguments.
while [[ $# -gt 0 ]]; do
  case $1 in
    --tag)
      IMAGE_TAG="$2"
      shift 2
      ;;
    --save)
      SAVE_IMAGE="true"
      shift
      ;;
    --help)
      echo "Usage: $0 [--tag TAG] [--save]"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Enable BuildKit.
export DOCKER_BUILDKIT=1

# Create a build timestamp (used if needed).
BUILD_TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Build the image.
docker buildx build \
  --file "$DOCKERFILE_PATH" \
  --tag "$IMAGE_NAME:$IMAGE_TAG" \
  --build-arg BUILD_TIMESTAMP="$BUILD_TIMESTAMP" \
  --progress=plain \
  --load \
  "$PROJECT_ROOT"

# Optionally save the image to a tarball.
if [ "${SAVE_IMAGE:-}" = "true" ]; then
  docker save "$IMAGE_NAME:$IMAGE_TAG" -o "${IMAGE_NAME}_${IMAGE_TAG}.tar"
fi

echo "To run the container, use:"
echo "docker run -p 3000:3000 $IMAGE_NAME:$IMAGE_TAG"
