# NearAI AWS Runner
A docker container that runs on AWS Lambda to run NearAI agents.
 * This is invoked by the NearAI Api server or NearAI cli.
 * The runner calls back to the NearAI Api server for inference,
to fetch agent code, and to fetch and store environments (store not implemented yet).


## Local testing
__Docker must be run from the root of the repository so the Dockerfile can pull in openapi_client.__

Note the dash before the framework name when passing a framework. The deploy script adds the dash but here it must be added manually.

Base framework `docker build -f aws_runner/Dockerfile --platform linux/amd64 --build-arg -t nearai-runner:test .`

LangGraph framework `docker build -f aws_runner/Dockerfile --platform linux/amd64 --build-arg FRAMEWORK=-langgraph -t nearai-runner:test .`

Then `docker run --platform linux/amd64 -p 9000:8080 nearai-runner:test` will start the server on port 9000. 

To call the server you will need a signedMessage for the auth param.
Then you can call the server with the following curl command.

```shell
auth_json=$(jq -c '.auth' ~/.nearai/config.json  | sed 's/"/\\"/g');
args='{"agents": "flatirons.near/example-travel-agent/1", "auth": "'; args+=$auth_json; args+='"}'
curl "http://localhost:9000/2015-03-31/functions/function/invocations" -d $args
```

If you want to specify the auth argument inline it should look like this (but with your credentials). This example
also includes an environment_id param for loading a previous environment.
```shell
curl "http://localhost:9000/2015-03-31/functions/function/invocations" \
-d @- <<'EOF'
  {
    "agents": "xela-agent",
    "environment_id":"environment_run_xela-tools-agent_541869e6753c41538c87cb6f681c6932",
    "auth":"{\"account_id\":\"your_account.near\",
        \"public_key\":\"ed25519:F5DeKFoya9fl35hapvpXxwReoksgi9a677JkniDIFLAW\",
        \"signature\":\"SIGNATURE_FIELD_FROM_A_REAL_SIGNATURE\",
        \"callback_url\":\"https://app.near.ai/",\"message\":\"Welcome to NEAR Talkbot app\"}"}
EOF
```

## Deployment
The docker image is built and pushed to the NearAI ECR repository. The image is then deployed to AWS Lambda using the AWS CLI.

Deploy a single framework to a single environment.
```shell
FRAMEWORK=langgraph ENV=production deploy.sh
```

Deploy all frameworks to all environments.
```shell
deploy.sh all
```

## Running against staging
A local api can use the staging or other remote runner environments by setting the server environment in hub/.env. 
This requires that you have appropriate system credentials for the runner environment 
(i.e. that you are yourself running remote runner environments).

Usually you would want to also allow the remote runner to call back to your local api to save the resulting environment.
To do this set up a tunnel to your local machine using ngrok or a similar service and set the API_URL in the hub/.env file.
```shell
SERVER_ENVIRONMENT=staging
API_URL=https://YOUR-ENDPOINT.ngrok.io
```
