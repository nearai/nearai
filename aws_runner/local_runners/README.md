You can run a multiple local runners to support multiple agents working in parallel. Hub will run agent in the corresponding local runner. If there are no available ports to create new runners, it will display the warning message. 

You can restart the hub to reset the runners/port mappings.

# How to use

1. Start local runners. This will start 3 local runners on a 9009-9011 ports

```bash
cd aws_runner/local_runners
docker-compose up -d
```

2. Add available runner ports to `hub/.env` and custom runner url with the %PORT% placeholder. For example:
```shell
AVAILABLE_LOCAL_RUNNER_PORTS=9009,9010,9011
CUSTOM_RUNNER_URL=http://localhost:%PORT%/2015-03-31/functions/function/invocations
```

3. Run the hub

```shell
fastapi dev app.py --port 8081
```

4. If you want to rebuild the docker image and restart all local runners, you can run the following command:

```bash
docker build -f aws_runner/Dockerfile --platform linux/amd64 --build-arg FRAMEWORK=-base -t nearai-runner:test . && cd aws_runner/local_runners &&  docker-compose up -d --force-recreate && cd ../..
```