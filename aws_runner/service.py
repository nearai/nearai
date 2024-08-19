# -*- coding: utf-8 -*-
import json
import os
import tarfile
from typing import Optional

from openapi_client.api_client import ApiClient
from openapi_client.configuration import Configuration
from partial_near_client import PartialNearClient
from runner.agent import Agent
from runner.environment import ENVIRONMENT_FILENAME, Environment

PATH = "/tmp/agent-runner-docker/environment-runs"
RUN_PATH = PATH + "/run"


def handler(event, context):
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
    max_iterations = int(params.get("max_iterations", 2))
    record_run = bool(params.get("record_run", True))

    new_environment_registry_id = run_with_environment(
        agents, auth_object, environment_id, new_message, max_iterations, record_run
    )
    if not new_environment_registry_id:
        return f"Run not recorded. Ran {agents} agent(s) with generated near client and environment {environment_id}"
    return new_environment_registry_id


def load_agent(client, agent):
    agent_code = client.get_agent(agent)
    return Agent(agent, RUN_PATH, agent_code)


def run_with_environment(
    agents: str,
    auth: dict,
    environment_id: str = None,
    new_message: str = None,
    max_iterations: int = 10,
    record_run: bool = True,
) -> Optional[str]:
    """Runs agent against environment fetched from id, optionally passing a new message to the environment."""
    configuration = Configuration(access_token=f"Bearer {json.dumps(auth)}", host="https://api.near.ai")
    client = ApiClient(configuration)
    near_client = PartialNearClient(client, auth)

    loaded_agents = [load_agent(near_client, agent) for agent in agents.split(",")]

    if environment_id:
        loaded_env = near_client.get_environment(environment_id)
        file = loaded_env
        os.makedirs(PATH, exist_ok=True)
        with open(f"{PATH}/{ENVIRONMENT_FILENAME}", "wb") as f:
            f.write(file)
            f.flush()
        with tarfile.open(f"{PATH}/environment.tar.gz", mode="r:gz") as tar:
            tar.extractall(RUN_PATH)

    env = Environment(RUN_PATH, loaded_agents, near_client)
    return env.run(new_message, record_run, environment_id, max_iterations)
