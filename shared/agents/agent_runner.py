import json
import os
import shutil
import time
from typing import Optional

import boto3

from shared.agents.agent import Agent
from shared.agents.environment import Environment
from shared.auth_data import AuthData
from shared.client_config import DEFAULT_API_URL, ClientConfig
from shared.inference_client import InferenceClient
from shared.partial_near_client import PartialNearClient

cloudwatch = boto3.client("cloudwatch", region_name="us-east-2")

PATH = "/tmp/agent-runner-docker/environment-runs"
RUN_PATH = PATH + "/run"


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
                        {"Name": "FunctionName", "Value": os.environ["AWS_LAMBDA_FUNCTION_NAME"]},
                    ],
                }
            ],
        )
    else:
        print(f"Would have written metric {metric_name} with value {value} to cloudwatch")


def get_local_agent_files(agent_identifier: str, additional_path: str = ""):
    """Fetches an agent from local filesystem."""
    base_path = os.path.expanduser(f"~/.nearai/registry/{agent_identifier}")

    paths = [base_path]
    if additional_path:
        paths.append(os.path.join(base_path, additional_path))

    results = []
    for path in paths:
        for root, _dirs, files in os.walk(path):
            for file in files:
                path = os.path.join(root, file)
                try:
                    with open(path, "r") as f:
                        result = f.read()
                    results.append({"filename": os.path.basename(path), "content": result})
                except Exception as e:
                    print(f"Error {path}: {e}")
    return results


def load_agent(client, agent, params: dict, account_id: str = "local", additional_path: str = "") -> Agent:
    agent_metadata = None

    if params["data_source"] == "registry":
        start_time = time.perf_counter()
        agent_files = client.get_agent(agent)
        stop_time = time.perf_counter()
        write_metric("GetAgentFromRegistry_Duration", stop_time - start_time)
        agent_metadata = client.get_agent_metadata(agent)
    elif params["data_source"] == "local_files":
        print("local_files")
        agent_files = get_local_agent_files(agent, additional_path)

        for file in agent_files:
            if os.path.basename(file["filename"]) == "metadata.json":
                agent_metadata = json.loads(file["content"])
                print(f"Loaded {agent_metadata} agents from {agent}")
                break

    if not agent_metadata:
        print(f"Missing metadata for {agent}")

    return Agent(agent, agent_files, agent_metadata or {})


class EnvironmentRun:
    def __init__(  # noqa: D107
        self, near_client: PartialNearClient, agents: list[Agent], env: Environment, thread_id, record_run: bool
    ) -> None:
        self.near_client = near_client
        self.agents = agents
        self.env = env
        self.thread_id = thread_id
        self.record_run = record_run

    def __del__(self) -> None:  # noqa: D105
        clear_temp_agent_files(self.agents)

    def run(self, new_message: str = "") -> Optional[str]:  # noqa: D102
        start_time = time.perf_counter()
        self.env.run(new_message, self.agents[0].max_iterations)
        new_environment = (
            save_environment(self.env, self.near_client, self.thread_id, write_metric) if self.record_run else None
        )
        stop_time = time.perf_counter()
        write_metric("ExecuteAgentDuration", stop_time - start_time)
        return new_environment


def start_with_environment(
    agents: str,
    auth: AuthData,
    thread_id,
    run_id,
    additional_path: str = "",
    params: Optional[dict] = None,
    print_system_log: bool = False,
) -> EnvironmentRun:
    """Initializes environment for agent runs."""
    print(
        f"Running with:\nagents: {agents}\nparams: {params}" f"\nthread_id: {thread_id}\nrun_id: {run_id}\nauth: {auth}"
    )
    params = params or {}
    api_url = str(params.get("api_url", DEFAULT_API_URL))
    user_env_vars: dict = params.get("user_env_vars", {})
    agent_env_vars: dict = params.get("agent_env_vars", {})

    if api_url != DEFAULT_API_URL:
        print(f"WARNING: Using custom API URL: {api_url}")

    near_client = PartialNearClient(api_url, auth)

    loaded_agents: list[Agent] = []

    for agent_name in agents.split(","):
        agent = load_agent(near_client, agent_name, params, auth.account_id, additional_path)
        # agents secrets has higher priority then agent metadata's env_vars
        agent.env_vars = {**agent.env_vars, **agent_env_vars.get(agent_name, {})}
        loaded_agents.append(agent)

    agent = loaded_agents[0]
    if "provider" in params:
        agent.model_provider = params["provider"]
    if "model" in params:
        agent.model = params["model"]
    if "temperature" in params:
        agent.model_temperature = params["temperature"]
    if "max_tokens" in params:
        agent.model_max_tokens = params["max_tokens"]

    client_config = ClientConfig(
        base_url=api_url + "/v1",
        auth=auth,
    )
    inference_client = InferenceClient(client_config)
    hub_client = client_config.get_hub_client()
    env = Environment(
        additional_path if additional_path else RUN_PATH,
        loaded_agents,
        inference_client,
        hub_client,
        thread_id,
        run_id,
        env_vars=user_env_vars,
        print_system_log=print_system_log,
    )
    if agent.welcome_title:
        print(agent.welcome_title)
    if agent.welcome_description:
        print(agent.welcome_description)
    env.add_agent_start_system_log(agent_idx=0)
    return EnvironmentRun(near_client, loaded_agents, env, thread_id, params.get("record_run", True))


def run_with_environment(
    agents: str,
    auth: AuthData,
    thread_id,
    run_id,
    additional_path: str = "",
    new_message: str = "",
    params: Optional[dict] = None,
    print_system_log: bool = False,
) -> Optional[str]:
    """Runs agent against environment fetched from id, optionally passing a new message to the environment."""
    environment_run = start_with_environment(agents, auth, thread_id, run_id, additional_path, params, print_system_log)
    return environment_run.run(new_message)


def clear_temp_agent_files(agents):
    for agent in agents:
        if agent.temp_dir and os.path.exists(agent.temp_dir):
            print("removed agent.temp_dir", agent.temp_dir)
            shutil.rmtree(agent.temp_dir)


def save_environment(env, client, base_id, metric_function=None) -> str:
    save_start_time = time.perf_counter()
    snapshot = env.create_snapshot()
    metadata = env.environment_run_info(base_id, "remote run")
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
