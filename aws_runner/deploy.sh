#!/bin/sh

## Deploy script for AWS Lambda Agent runner
## This script must be run from the root of the repository so the Docker build can pull in openapi_client.
##
## Usage: aws_runner/deploy.sh [all]
##    FRAMEWORK=base|langgraph ENV=staging|production aws_runner/deploy.sh
## Examples:
##    aws_runner/deploy.sh all
##    FRAMEWORK=base ENV=staging aws_runner/deploy.sh
##
## Builds the Docker image, pushes it to ECR, and updates the Lambda function to use it.

ALL_FRAMEWORKS=("minimal" "langgraph-0-1-4" "langgraph-0-2-26" "standard" "agentkit")
ALL_ENVIRONMENTS=("staging" "production")

deploy() {
  FRAMEWORK="-${FRAMEWORK:-"minimal"}"
  ENV="${ENV:-"staging"}-"
  RUNNER_TYPE=${RUNNER_TYPE:-"py_runner"}
  VERSION=$(date +%Y%m%d_%H%M%S)

  echo "Deploying ${ENV}agent-runner${FRAMEWORK} version ${VERSION}"

  aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin 543900120763.dkr.ecr.us-east-2.amazonaws.com

  docker build -f aws_runner/${RUNNER_TYPE}/Dockerfile --platform linux/amd64 --build-arg FRAMEWORK=${FRAMEWORK} --provenance=false -t nearai-runner${FRAMEWORK}:${VERSION} .
  if [ $? -ne 0 ]; then
    echo "Docker build failed"
    exit 1
  fi

  COMPRESSED_SIZE=$(docker images nearai-runner${FRAMEWORK}:${VERSION} --format "{{.Size}}")
  COMPRESSED_SIZE_MB=$(echo $COMPRESSED_SIZE | sed 's/GB//' | awk '{print int($1*1000)}')
    
  echo "==================================="
  echo "Image size information:"
  echo "Compressed size: $COMPRESSED_SIZE"
  echo "AWS Lambda limit: 10GB uncompressed"
  echo "==================================="
    
  if [ $COMPRESSED_SIZE_MB -gt 9000 ]; then
    echo "WARNING: Image may exceed AWS Lambda's 10GB uncompressed size limit!"
    echo "Deployment might fail."
    read -p "Do you want to proceed with deployment? (y/n): " CONFIRM
    if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
      echo "Deployment cancelled."
      exit 0
    fi
  fi
  
  echo "Proceeding with deployment..."

  # Tag with version and latest
  docker tag nearai-runner${FRAMEWORK}:${VERSION} 543900120763.dkr.ecr.us-east-2.amazonaws.com/nearai-runner${FRAMEWORK}:${VERSION}
  docker tag nearai-runner${FRAMEWORK}:${VERSION} 543900120763.dkr.ecr.us-east-2.amazonaws.com/nearai-runner${FRAMEWORK}:latest
  
  # Push both tags
  docker push 543900120763.dkr.ecr.us-east-2.amazonaws.com/nearai-runner${FRAMEWORK}:${VERSION}
  if [ $? -ne 0 ]; then
    echo "Docker push for version failed"
    exit 1
  fi

  docker push 543900120763.dkr.ecr.us-east-2.amazonaws.com/nearai-runner${FRAMEWORK}:latest
  if [ $? -ne 0 ]; then
    echo "Docker push for latest failed"
    exit 1
  fi

  # Update Lambda and wait for update to complete
  aws lambda update-function-code --region us-east-2 \
    --function-name ${ENV}agent-runner${FRAMEWORK} \
    --image-uri 543900120763.dkr.ecr.us-east-2.amazonaws.com/nearai-runner${FRAMEWORK}:${VERSION}
  if [ $? -ne 0 ]; then
    echo "Lambda update failed"
    exit 1
  fi
    echo "Waiting for Lambda update to complete..."
    aws lambda wait function-updated --function-name ${ENV}agent-runner${FRAMEWORK} --region us-east-2
  }

if [ "$1" = "all" ]; then
  echo "Deploying all frameworks to all environments"
  for EACH_FRAMEWORK in "${ALL_FRAMEWORKS[@]}"; do
    for EACH_ENV in "${ALL_ENVIRONMENTS[@]}"; do
      FRAMEWORK=$EACH_FRAMEWORK ENV=$EACH_ENV deploy
    done
  done
else
  deploy
fi
