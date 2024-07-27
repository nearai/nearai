# -*- coding: utf-8 -*-
import json
import os

from openapi_client.api_client import ApiClient
from openapi_client.configuration import Configuration
from runner.agent import Agent
from runner.environment import Environment
from partial_near_client import PartialNearClient


def handler(event, context):
    required_params = ["agents", "environment_id", "auth"]
    agents = event.get("agents")
    environment_id = event.get("environment_id")
    auth = event.get("auth")
    if not agents or not environment_id or not auth:
        missing = list(filter(lambda x: event.get(x) is (None or ""), required_params))
        return f"Missing required parameters: {missing}"

    auth_object = json.loads(auth)
    run_with_environment(agents, environment_id, auth_object)

    return "Ran hardcoded xela agent with generated near client and new environment"


def load_agent():
    root = os.environ.get("LAMBDA_TASK_ROOT")
    with open(os.path.join(f"{root}/runner", "xela_agent_v4.py")) as f:
        return Agent("xela", "v4", f.read())


def run_with_environment(
        agents: str,
        environment_id: str,
        auth,
        max_iterations: int = 10,
        record_run: str = "true",
        load_env: str = None,
):
    """Runs agent against environment fetched from id, optionally passing a new message to the environment."""
    # _agents = [load_agent(agent) for agent in agents.split(",")]
    test_agent = load_agent()  # hardcoded (local code) agent for now
    agents = [test_agent]
    configuration = Configuration(
        access_token=f"Bearer {json.dumps(auth)}",
        host="https://api.neara.ai"
    )
    client = ApiClient(configuration)
    partial_client = PartialNearClient(client)
    env = Environment("/tmp/environment-runs/agent-runner-docker", agents, auth, partial_client)
    test_task = "Build a game of checkers"
    env.run_task(test_task, False, load_env, max_iterations)