# NEAR AI AWS Runner
A docker container that runs on AWS Lambda to run NEAR AI agents.
 * This is invoked by the NEAR AI Api server or the NEAR AI cli agent run_remote command.
 * The runner calls back to the NEAR AI Api server for inference, to fetch agent code, 
and to fetch and store environments. An environment is the files that result from an agent run, which will always
include chat.txt and system.log.txt files.


## Local testing
__Docker must be run from the root of the repository so the Dockerfile can pull in the openapi_client and shared directories.__

Note the dash before the framework name when passing a framework. The deploy script adds the dash but here it must be added manually.

Minimal framework `docker build -f aws_runner/py_runner/Dockerfile --platform linux/amd64 --build-arg FRAMEWORK=-minimal -t nearai-runner:test .`

Typescript framework `docker build -f aws_runner/ts_runner/Dockerfile --platform linux/amd64 --build-arg FRAMEWORK=-ts -t nearai-runner:test .`

LangGraph framework `docker build -f aws_runner/py_runner/Dockerfile --platform linux/amd64 --build-arg FRAMEWORK=-langgraph-1-4 -t nearai-runner:test .`

Then `docker run --platform linux/amd64 -p 9001:8080 nearai-runner:test` will start the server on port 9000.

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
    "agents": "flatirons.near/example-travel-agent/1",
    "environment_id":"flatirons.near/environment_run_flatirons.near_example-travel-agent_1_e03703aeebd8487895d5cad37a2d5f9d/0",
    "auth":"{\"account_id\":\"your_account.near\",
        \"public_key\":\"ed25519:F5DeKFoya9fl35hapvpXxwReoksgi9a677JkniDIFLAW\",
        \"signature\":\"SIGNATURE_FIELD_FROM_A_REAL_SIGNATURE\",
        \"callback_url\":\"https://app.near.ai/",\"message\":\"Welcome to NEAR Talkbot app\"}"}
EOF
```

### Local testing with Hub UI

By default, an AWS Lambda runner is used to execute the agent's code, but you can switch to using local runner by specifying the environment variables (which can be set in `/hub/.env`):

```
RUNNER_ENVIRONMENT="custom_runner"
CUSTOM_RUNNER_URL=http://localhost:9000/2015-03-31/functions/function/invocations
API_URL=http://host.docker.internal:8081
```

It might be useful to provide `API_URL` into the `docker run` command to use local Hub API instead of NEAR AI Hub API.

`docker run -e API_URL=http://host.docker.internal:8081 --platform linux/amd64 -p 9009:8080 nearai-runner:test`


### Local data source 

If you want to use local files instead of the NEAR AI registry to run agents that are not yet published:

- mount  `~/.nearai/registry` to the docker image (add `-v ~/.nearai/registry:/root/.nearai/registry` to `docker run` command)
- specify `DATA_SOURCE="local_files"`:
  - in the Hub environment variables (`hub/.env`) for runner to use local files 
  - the Hub UI environment variables (`/hub/demo/.env`) for UI to use local files

## Deployment
The docker image is built and pushed to the NEAR AI ECR repository. The image is then deployed to AWS Lambda using the AWS CLI.

Deploy a single framework to a single environment.
```shell
FRAMEWORK=langgraph ENV=production deploy.sh
```

Deploy all frameworks to all environments.
```shell
deploy.sh all
```

Deploying the TypeScript runner requires providing a RUNNER_TYPE environment variable
```shell
FRAMEWORK=ts ENV=production RUNNER_TYPE=ts_runner ./aws_runner/deploy.sh
```

## Running against staging
A local api can use the staging or other remote runner environments by setting the server environment in hub/.env. 
This requires that you have appropriate system credentials for the runner environment 
(i.e. that you are yourself running remote runner environments).

Usually you would want to also allow the remote runner to call back to your local api to save the resulting environment.
To do this set up a tunnel to your local machine using ngrok or a similar service and set the API_URL in the hub/.env file.
```shell
RUNNER_ENVIRONMENT=staging
API_URL=https://YOUR-ENDPOINT.ngrok.io
```