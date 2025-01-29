# NearAI CVM Runner

NEAR AI Agent runner for Confidential Virtual Machines.

## Build

From nearai root directory:
```bash
docker buildx build --no-cache --load --platform linux/amd64 -t nearai_cvm_pool:latest -f .docker/Dockerfile.cvm_pool .
```

## Build and push

```bash
export OWNER=plgnai
docker buildx build --no-cache --load --push --platform linux/amd64 -t ${OWNER}/nearai_cvm_pool:latest -f .docker/Dockerfile.cvm_pool .
```

## Run

```bash
export HOST_PORT=8080
export PRIVATE_ML_SDK_PATH=/home/ubuntu/private-ml-sdk
docker run --platform linux/amd64 -e PRIVATE_ML_SDK_PATH=${PRIVATE_ML_SDK_PATH} -p ${HOST_PORT}:80 nearai_cvm_pool:latest
```
