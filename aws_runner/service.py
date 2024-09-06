# -*- coding: utf-8 -*-
import json
import os
import tarfile
import time
from subprocess import call
from typing import Optional

import boto3
from openapi_client.api_client import ApiClient
from openapi_client.configuration import Configuration
from partial_near_client import PartialNearClient
from runner.agent import Agent
from runner.environment import ENVIRONMENT_FILENAME, Environment

cloudwatch = boto3.client("cloudwatch", region_name="us-east-2")

PATH = "/tmp/agent-runner-docker/environment-runs"
RUN_PATH = PATH + "/run"
FUNCTION_NAME = os.environ["AWS_LAMBDA_FUNCTION_NAME"]
DEFAULT_API_URL = "https://api.near.ai"


def handler(event, context):
    start_time = time.perf_counter()
    required_params = ["agents", "auth"]
    agents = event.get("agents")
    auth = event.get("auth")
    if not agents or not auth:
        missing = list(filter(lambda x: event.get(x) is (None or ""), required_params))
        return f"Missing required parameters: {missing}"

    auth_object = auth if isinstance(auth, dict) else json.loads(auth)
    # todo validate signature

    environment_id = event.get("environment_id")
    new_message = event.get("new_message")

    params = event.get("params", {})

    new_environment_registry_id = run_with_environment(agents, auth_object, environment_id, new_message, params)
    if not new_environment_registry_id:
        return f"Run not recorded. Ran {agents} agent(s) with generated near client and environment {environment_id}"

    call("rm -rf /tmp/..?* /tmp/.[!.]* /tmp/*", shell=True)
    stop_time = time.perf_counter()
    write_metric("TotalRunnerDuration", stop_time - start_time)
    return new_environment_registry_id


def write_metric(metric_name, value, unit="Milliseconds"):
    cloudwatch.put_metric_data(
        Namespace="NearAI",
        MetricData=[
            {
                "MetricName": metric_name,
                "Value": value,
                "Unit": unit,
                "Dimensions": [
                    {"Name": "FunctionName", "Value": FUNCTION_NAME},
                ],
            }
        ],
    )


def load_agent(client, agent):
    start_time = time.perf_counter()
    agent_code = client.get_agent(agent)
    stop_time = time.perf_counter()
    write_metric("GetAgentFromRegistry_Duration", stop_time - start_time)
    return Agent(agent, RUN_PATH, agent_code)


def run_with_environment(
    agents: str,
    auth: dict,
    environment_id: str = None,
    new_message: str = None,
    params: dict = None,
) -> Optional[str]:
    """Runs agent against environment fetched from id, optionally passing a new message to the environment."""
    params = params or {}
    max_iterations = int(params.get("max_iterations", 2))
    record_run = bool(params.get("record_run", True))
    api_url = str(params.get("api_url", DEFAULT_API_URL))

    if api_url != DEFAULT_API_URL:
        print(f"WARNING: Using custom API URL: {api_url}")

    configuration = Configuration(access_token=f"Bearer {json.dumps(auth)}", host=api_url)
    client = ApiClient(configuration)
    near_client = PartialNearClient(client, auth)

    loaded_agents = [load_agent(near_client, agent) for agent in agents.split(",")]

    if environment_id:
        start_time = time.perf_counter()
        loaded_env = near_client.get_environment(environment_id)
        stop_time = time.perf_counter()
        write_metric("GetEnvironmentFromRegistry_Duration", stop_time - start_time)
        file = loaded_env
        os.makedirs(PATH, exist_ok=True)
        with open(f"{PATH}/{ENVIRONMENT_FILENAME}", "wb") as f:
            f.write(file)
            f.flush()
        with tarfile.open(f"{PATH}/environment.tar.gz", mode="r:gz") as tar:
            tar.extractall(RUN_PATH)

    env = Environment(RUN_PATH, loaded_agents, near_client, metric_function=write_metric)
    start_time = time.perf_counter()
    run_result = env.run(new_message, record_run, environment_id, max_iterations)
    stop_time = time.perf_counter()
    write_metric("ExecuteAgentDuration", stop_time - start_time)
    return run_result
