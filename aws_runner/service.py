# -*- coding: utf-8 -*-
import json
import os
import shutil
import tarfile
import time
from subprocess import call
from typing import Optional

import boto3
from partial_near_client import ENVIRONMENT_FILENAME, PartialNearClient
from runner.agent import Agent
from runner.environment import Environment

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
    if os.environ.get("AWS_ACCESS_KEY_ID"):  # running in lambda or locally passed credentials
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
    else:
        print(f"Would have written metric {metric_name} with value {value} to cloudwatch")


def load_agent(client, agent, agent_env_vars):
    env_vars = agent_env_vars.get(agent, {})
    start_time = time.perf_counter()
    agent_files = client.get_agent(agent)
    stop_time = time.perf_counter()
    write_metric("GetAgentFromRegistry_Duration", stop_time - start_time)
    agent_metadata = client.get_agent_metadata(agent)

    return Agent(agent, RUN_PATH, agent_files, env_vars, agent_metadata)


def clear_temp_agent_files(agents):
    for agent in agents:
        if agent.temp_dir and os.path.exists(agent.temp_dir):
            print("removed agent.temp_dir", agent.temp_dir)
            shutil.rmtree(agent.temp_dir)


def save_environment(env, client, run_id, base_id, metric_function=None) -> str:
    save_start_time = time.perf_counter()
    snapshot = env.create_snapshot()
    metadata = env.environment_run_info(run_id, base_id, "remote run")
    name = metadata["name"]
    request_start_time = time.perf_counter()
    registry_id = client.save_environment(snapshot, metadata)
    request_stop_time = time.perf_counter()
    if metric_function:
        metric_function("SaveEnvironmentToRegistry_Duration", request_stop_time - request_start_time)
    print(
        f"Saved environment {registry_id} to registry. To load use flag `--load-env={registry_id}`. "
        f"or `--load-env={name}`"
    )
    save_stop_time = time.perf_counter()
    if metric_function:
        metric_function("SaveEnvironment_Duration", save_stop_time - save_start_time)
    return registry_id


def run_with_environment(
    agents: str, auth: dict, environment_id: str = None, new_message: str = None, params: dict = None
) -> Optional[str]:
    """Runs agent against environment fetched from id, optionally passing a new message to the environment."""
    params = params or {}
    max_iterations = int(params.get("max_iterations", 2))
    record_run = bool(params.get("record_run", True))
    api_url = str(params.get("api_url", DEFAULT_API_URL))
    agent_env_vars: dict = params.get("agent_env_vars", {})
    user_env_vars: dict = params.get("user_env_vars", {})

    if api_url != DEFAULT_API_URL:
        print(f"WARNING: Using custom API URL: {api_url}")

    near_client = PartialNearClient(api_url, auth)

    loaded_agents = [load_agent(near_client, agent, agent_env_vars) for agent in agents.split(",")]

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

        try:
            with tarfile.open(f"{PATH}/environment.tar.gz", mode="r") as tar:
                tar.extractall(RUN_PATH)
        except tarfile.ReadError:
            print("The file is not a valid tar archive.")

    env = Environment(RUN_PATH, loaded_agents, near_client, env_vars=user_env_vars)
    start_time = time.perf_counter()
    run_id = env.run(new_message, max_iterations)
    new_environment = save_environment(env, near_client, run_id, environment_id, write_metric) if record_run else None
    clear_temp_agent_files(loaded_agents)
    stop_time = time.perf_counter()
    write_metric("ExecuteAgentDuration", stop_time - start_time)
    return new_environment
