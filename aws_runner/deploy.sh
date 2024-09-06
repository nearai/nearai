#!/bin/sh

ALL_FRAMEWORKS=("base" "langgraph")
ALL_ENVIRONMENTS=("staging" "production")

deploy() {
  FRAMEWORK="-${FRAMEWORK:-"base"}"
  ENV="${ENV:-"staging"}-"

  echo "Deploying ${ENV}agent-runner${FRAMEWORK}"

  aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin 543900120763.dkr.ecr.us-east-2.amazonaws.com
  docker build --platform linux/amd64 --build-arg FRAMEWORK=${FRAMEWORK} -t nearai-runner${FRAMEWORK} .
  docker tag nearai-runner${FRAMEWORK}:latest 543900120763.dkr.ecr.us-east-2.amazonaws.com/nearai-runner${FRAMEWORK}:latest
  docker push 543900120763.dkr.ecr.us-east-2.amazonaws.com/nearai-runner${FRAMEWORK}:latest
  aws lambda update-function-code --region us-east-2 \
             --function-name ${ENV}agent-runner${FRAMEWORK} \
             --image-uri 543900120763.dkr.ecr.us-east-2.amazonaws.com/nearai-runner${FRAMEWORK}:latest
#  aws lambda publish-version --region us-east-2 --function-name ${ENV}agent-runner${FRAMEWORK}
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
