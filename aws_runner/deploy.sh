#!/bin/sh

aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin 543900120763.dkr.ecr.us-east-2.amazonaws.com
docker build --platform linux/amd64 -t nearai-runner .
docker tag nearai-runner:latest 543900120763.dkr.ecr.us-east-2.amazonaws.com/nearai-runner:latest
docker push 543900120763.dkr.ecr.us-east-2.amazonaws.com/nearai-runner:latest
aws lambda update-function-code --region us-east-2 \
           --function-name agent-runner-docker \
           --image-uri 543900120763.dkr.ecr.us-east-2.amazonaws.com/nearai-runner:latest
#aws lambda publish-version --region us-east-2 \
#    --function-name agent-runner-docker