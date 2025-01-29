# NearAI CVM Runner

NEAR AI Agent runner for Confidential Virtual Machines. To be ran in a CVM.

## Build

From nearai root directory:
```bash
docker buildx build --no-cache --load --platform linux/amd64 -t nearai_runner:latest -f .docker/Dockerfile.cvm_runner .
```

## Build and push

```bash
export OWNER=plgnai
docker buildx build --no-cache --load --push --platform linux/amd64 -t ${OWNER}/nearai_runner:latest -f .docker/Dockerfile.cvm_runner .
```

## Run

```bash
export HOST_PORT=8080
docker run --platform linux/amd64 -p ${HOST_PORT}:80 nearai_runner:latest
```
