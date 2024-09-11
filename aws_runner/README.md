# NearAI AWS Runner
A docker container that runs on AWS Lambda to run NearAI agents.
 * This is invoked by the NearAI Api server or NearAI cli.
 * The runner calls back to the NearAI Api server for inference,
to fetch agent code, and to fetch and store environments (store not implemented yet).


## Local testing
`docker build --platform linux/amd64 --build-arg FRAMEWORK=-base -t nearai-runner:test .`

`docker run -e AWS_ACCESS_KEY_ID=YOUR_KEY -e AWS_SECRET_ACCESS_KEY=YOUR_SECRET --platform linux/amd64 -p 9000:8080 nearai-runner:test`
This will start the server on port 9000.

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