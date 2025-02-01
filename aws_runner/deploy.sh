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

ALL_FRAMEWORKS=("base" "langgraph-0-1-4" "langgraph-0-2-26" "web-agent" "agentkit")
ALL_ENVIRONMENTS=("staging" "production")

deploy() {
  FRAMEWORK="-${FRAMEWORK:-"base"}"
  ENV="${ENV:-"staging"}-"
  VERSION=$(date +%Y%m%d_%H%M%S)

  echo "Deploying ${ENV}agent-runner${FRAMEWORK} version ${VERSION}"

  aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin 543900120763.dkr.ecr.us-east-2.amazonaws.com
  
  docker build -f aws_runner/Dockerfile --platform linux/amd64 --build-arg FRAMEWORK=${FRAMEWORK} -t nearai-runner${FRAMEWORK}:${VERSION} .
  
  # Tag with version and latest
  docker tag nearai-runner${FRAMEWORK}:${VERSION} 543900120763.dkr.ecr.us-east-2.amazonaws.com/nearai-runner${FRAMEWORK}:${VERSION}
  docker tag nearai-runner${FRAMEWORK}:${VERSION} 543900120763.dkr.ecr.us-east-2.amazonaws.com/nearai-runner${FRAMEWORK}:latest
  
  # Push both tags
  docker push 543900120763.dkr.ecr.us-east-2.amazonaws.com/nearai-runner${FRAMEWORK}:${VERSION}
  docker push 543900120763.dkr.ecr.us-east-2.amazonaws.com/nearai-runner${FRAMEWORK}:latest
  
  # Update Lambda and wait for update to complete
  aws lambda update-function-code --region us-east-2 \
    --function-name ${ENV}agent-runner${FRAMEWORK} \
    --image-uri 543900120763.dkr.ecr.us-east-2.amazonaws.com/nearai-runner${FRAMEWORK}:${VERSION}

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
