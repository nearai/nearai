# -*- coding: utf-8 -*-
import json
import os
import tarfile

from openapi_client.api_client import ApiClient
from openapi_client.configuration import Configuration
from partial_near_client import PartialNearClient
from runner.agent import Agent
from runner.environment import Environment

PATH = "/tmp/agent-runner-docker/environment-runs"
RUN_PATH = PATH + "/run"


def handler(event, context):
    required_params = ["agents", "environment_id", "auth"]
    agents = event.get("agents")
    environment_id = event.get("environment_id")
    new_message = event.get("new_message")
    auth = event.get("auth")
    if not agents or not auth:
        missing = list(filter(lambda x: event.get(x) is (None or ""), required_params))
        return f"Missing required parameters: {missing}"

    auth_object = json.loads(auth)
    run_with_environment(agents, auth_object, environment_id, new_message, 2)  # fewer iterations for testing

    return f"Ran {agents} agent(s) with generated near client and environment {environment_id}"


def load_agent(client, agent):
    agent_code = client.get_agent(agent)
    return Agent(agent, RUN_PATH, agent_code)


def run_with_environment(
    agents: str, auth, environment_id: str = None, new_message: str = None, max_iterations: int = 10
):
    """Runs agent against environment fetched from id, optionally passing a new message to the environment."""
    configuration = Configuration(access_token=f"Bearer {json.dumps(auth)}", host="https://api.near.ai")
    client = ApiClient(configuration)
    near_client = PartialNearClient(client)

    loaded_agents = [load_agent(near_client, agent) for agent in agents.split(",")]

    if environment_id:
        loaded_env = near_client.get_environment(environment_id)
        file = loaded_env
        os.makedirs(PATH, exist_ok=True)
        with open(f"{PATH}/environment.tar.gz", "wb") as f:
            f.write(file)
            f.flush()
        with tarfile.open(f"{PATH}/environment.tar.gz", mode="r:gz") as tar:
            tar.extractall(RUN_PATH)

    env = Environment(RUN_PATH, loaded_agents, auth, near_client)
    env.run_task(new_message, False, environment_id, max_iterations)
