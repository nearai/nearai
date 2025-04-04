#!/bin/bash
set -euo pipefail

# Determine script and project root directories.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

IMAGE_NAME="guest_manager"
IMAGE_TAG="latest"
DOCKERFILE_PATH="${SCRIPT_DIR}/Dockerfile"
REGISTRY=""
PUBLISH=false

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
    --publish)
      PUBLISH=true
      REGISTRY="$2"
      shift 2
      ;;
    --help)
      echo "Usage: $0 [--tag TAG] [--save] [--publish REGISTRY]"
      echo "  --tag TAG       Specify image tag (default: latest)"
      echo "  --save         Save image to tarball"
      echo "  --publish REGISTRY  Push image to specified registry (e.g., docker.io/username)"
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
docker build \
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

# Optionally publish to registry
if [ "$PUBLISH" = true ]; then
  if [ -z "$REGISTRY" ]; then
    echo "Error: Registry must be specified with --publish"
    exit 1
  fi
  FULL_IMAGE_NAME="${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
  docker tag "$IMAGE_NAME:$IMAGE_TAG" "$FULL_IMAGE_NAME"
  docker push "$FULL_IMAGE_NAME"
  echo "Published image to: $FULL_IMAGE_NAME"
fi

echo "To run the container, use:"
echo "docker run --network=host -v /var/run/docker.sock:/var/run/docker.sock $IMAGE_NAME:$IMAGE_TAG"
