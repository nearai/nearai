# -*- coding: utf-8 -*-
import io
import json
import logging
import os
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from subprocess import call
from typing import Optional

import boto3
from ddtrace import patch_all, tracer
from nearai.agents.agent import Agent, get_local_agent_files
from nearai.agents.analytics import RunnerMetrics
from nearai.agents.environment import Environment, is_debug_mode
from nearai.aws_runner.partial_near_client import PartialNearClient
from nearai.registry import get_registry_folder, resolve_local_path
from nearai.shared.auth_data import AuthData
from nearai.shared.client_config import ClientConfig
from nearai.shared.inference_client import InferenceClient
from nearai.shared.near.sign import SignatureVerificationResult, verify_signed_message
from nearai.shared.provider_models import PROVIDER_MODEL_SEP
from openai import OpenAI

# Initialize Datadog tracing
if os.environ.get("DD_API_KEY"):
    patch_all()

OUTPUT_PATH = "/tmp/nearai-agent-runner"
DEFAULT_API_URL = "https://api.near.ai"
RUNNER_LOG_PATH = "/tmp/nearai-agent-runner/runner_log.txt"
RUNNER_LOG_FILENAME = "runner_log.txt"

# Local caches
provider_models_cache = None
provider_models_cache_time = None
local_agent_cache: dict[str, Agent] = {}


def create_cloudwatch():
    if (
        os.environ.get("AWS_ACCESS_KEY_ID")
        and os.environ.get("AWS_SECRET_ACCESS_KEY")
        and os.environ.get("AWS_LAMBDA_FUNCTION_NAME")
    ):
        return boto3.client("cloudwatch", region_name="us-east-2")
    return None


def load_protected_variables():
    variables = {}

    # Remove AWS credentials and HUB API KEYS from the environment variables.
    # These variables are typically set automatically in AWS Lambda or other environments
    # and may expose sensitive information if not handled properly.
    keys_to_remove = [
        "AWS_ACCESS_KEY_ID",  # Access key ID for AWS
        "AWS_SECRET_ACCESS_KEY",  # Secret access key for AWS
        "FASTNEAR_APY_KEY",  # API KEY for FastNear RPC
        "RUNNER_API_KEY",  # API KEY for a NEAR AI Runner
    ]

    # Loop through the list of keys and delete them from the environment if they exist.
    for key in keys_to_remove:
        if key in os.environ:
            variables[key] = os.environ[key]
            del os.environ[key]

    return variables


cloudwatch = create_cloudwatch()
protected_vars = load_protected_variables()


@tracer.wrap(service="aws-runner", resource="lambda_handler")
def handler(event, context):
    runner_metrics = RunnerMetrics()
    start_time = time.perf_counter()
    required_params = ["agents", "auth"]
    agents = event.get("agents")
    auth = event.get("auth")
    if not agents or not auth:
        missing = list(filter(lambda x: event.get(x) is (None or ""), required_params))
        return f"Missing required parameters: {missing}"

    auth_object = auth if isinstance(auth, AuthData) else AuthData(**auth)
    start_time_val = time.perf_counter()
    verification_result = verify_signed_message(
        auth_object.account_id,
        auth_object.public_key,
        auth_object.signature,
        auth_object.message,
        auth_object.nonce,
        auth_object.recipient,
        auth_object.callback_url,
    )

    if verification_result == SignatureVerificationResult.VERIFY_ACCESS_KEY_OWNER_SERVICE_NOT_AVAILABLE:
        write_metric("AdminNotifications", "SignatureAccessKeyVerificationServiceFailed", "Count")
    elif not verification_result:
        return "Unauthorized: Invalid signature"
    else:
        # signature is valid
        stop_time_val = time.perf_counter()
        write_metric("VerifySignatureDuration", stop_time_val - start_time_val)

    thread_id = event.get("thread_id")
    run_id = event.get("run_id")

    params = event.get("params", {})

    user_env_vars = params.get("user_env_vars", {})
    debug_mode = is_debug_mode(user_env_vars if user_env_vars else {})

    api_url = str(params.get("api_url", DEFAULT_API_URL))
    client_config = ClientConfig(
        base_url=api_url + "/v1",
        auth=auth,
    )
    hub_client = client_config.get_hub_client()

    if debug_mode:
        start_runner_log(params, hub_client, thread_id)

    new_thread_id = run_with_environment(
        agents, auth_object, thread_id, run_id, params=params, runner_metrics=runner_metrics, hub_client=hub_client
    )
    if not new_thread_id:
        return f"Run not recorded. Ran {agents} agent(s)."
    stop_time = time.perf_counter()
    write_metric("RunnerExecutionFinishedDuration", stop_time - start_time)
    call("rm -rf /tmp/..?* /tmp/.[!.]* /tmp/*", shell=True)
    stop_time = time.perf_counter()
    write_metric("TotalRunnerDuration", stop_time - start_time)
    return new_thread_id


def start_runner_log(params: dict, hub_client: OpenAI, thread_id):
    existing_logger = logging.getLogger("runner_logger")
    existing_logger.handlers = []

    # Thread pool for async operations
    thread_pool = ThreadPoolExecutor(max_workers=2)

    def logger(log: str, level=logging.INFO):
        # NOTE: Do not call prints in this function.
        logger = logging.getLogger("runner_logger")
        if not logger.handlers:
            # Configure the logger if it hasn't been set up yet
            logger.setLevel(logging.DEBUG)
            log_dir = os.path.dirname(RUNNER_LOG_PATH)
            if not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
            file_handler = logging.FileHandler(RUNNER_LOG_PATH)
            formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        # Log the message
        logger.log(level, log)
        # Force the handler to write to disk
        for handler in logger.handlers:
            handler.flush()

        # Upload to hub asynchronously
        def upload_log_async():
            log_path = RUNNER_LOG_PATH
            if os.path.exists(log_path):
                try:
                    with open(log_path, "r") as f:
                        content = f.read()
                    # Only upload if there's content
                    if content:
                        file = hub_client.files.create(
                            file=(RUNNER_LOG_FILENAME, content, "text/plain"), purpose="assistants"
                        )
                        hub_client.beta.threads.messages.create(
                            thread_id=thread_id,
                            role="assistant",
                            content=f"Output file: {RUNNER_LOG_FILENAME}",
                            attachments=[{"file_id": file.id}],
                            metadata={"message_type": "system:output_file"},
                        )
                except Exception:
                    # Silently handle exceptions to avoid breaking the logger
                    pass

        # Submit the upload task to thread pool (fire and forget)
        thread_pool.submit(upload_log_async)

    # Create a custom writer that logs and writes to buffer
    class LoggingWriter:
        # Static class variable to prevent recursion
        _in_write_operation = False

        def __init__(self, buffer, log_func, stream_name):
            self.buffer = buffer
            self.log_func = log_func
            self.stream_name = stream_name

        def write(self, msg):
            # Write to buffer regardless of recursion state
            self.buffer.write(msg)

            # Only log if not already in a write operation and message is not empty
            if not LoggingWriter._in_write_operation and msg.strip():
                try:
                    # Set recursion flag before logging
                    LoggingWriter._in_write_operation = True
                    self.log_func(f"[RUNNER {self.stream_name}] {msg.strip()}")
                finally:
                    # Always reset the flag, even if an exception occurs
                    LoggingWriter._in_write_operation = False

        def flush(self):
            self.buffer.flush()

    if params["data_source"] == "registry":
        stdout_buffer = io.StringIO()
        sys.stdout = LoggingWriter(stdout_buffer, logger, "STDOUT")
        stderr_buffer = io.StringIO()
        sys.stderr = LoggingWriter(stderr_buffer, logger, "STDERR")


def write_metric(metric_name, value, unit="Milliseconds", verbose=True):
    if cloudwatch and value:  # running in lambda or locally passed credentials
        try:
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
        except Exception as e:
            print("Caught Error writing metric to CloudWatch: ", e)
    elif verbose:
        print(f"[DEBUG] • Would have written metric {metric_name} with value {value} to cloudwatch")


def load_agent(client, agent: str, params: dict, additional_path: str = "", verbose=True) -> Agent:
    agent_metadata = None

    if params["data_source"] == "registry":
        use_cache = os.getenv("USE_AGENT_CACHE", "true").lower() == "true"

        global local_agent_cache
        if use_cache:
            if agent in local_agent_cache:
                cached_agent = local_agent_cache[agent]

                # recreate the agent object to ensure it has all data from constructor
                full_agent = Agent(
                    agent,
                    cached_agent.agent_files,
                    cached_agent.metadata or {},
                    change_to_temp_dir=params.get("change_to_agent_temp_dir", True),
                )

                print(f"Using {agent} from cache in {full_agent.temp_dir}")
                return full_agent

        start_time = time.perf_counter()
        agent_files = client.get_agent(agent)
        stop_time = time.perf_counter()
        write_metric("GetAgentFromRegistry_Duration", stop_time - start_time, verbose=verbose)
        start_time = time.perf_counter()
        agent_metadata = client.get_agent_metadata(agent)
        stop_time = time.perf_counter()
        write_metric("GetMetadataFromRegistry_Duration", stop_time - start_time, verbose=verbose)
        full_agent = Agent(
            agent, agent_files, agent_metadata or {}, change_to_temp_dir=params.get("change_to_agent_temp_dir", True)
        )
        local_agent_cache[full_agent.identifier] = full_agent
        print(f"Saving {full_agent.identifier} from {full_agent.temp_dir} to cache")
        return full_agent
    elif params["data_source"] == "local_files":
        agent = agent.replace(f"{get_registry_folder()}/", "")
        path = resolve_local_path(Path(additional_path if additional_path else agent))
        agent_files = get_local_agent_files(path)

        for file in agent_files:
            if os.path.basename(file) == "metadata.json":
                with open(file) as f:
                    agent_metadata = json.load(f)
                if verbose:
                    agent_info = f"""[DEBUG]   • Name: {agent_metadata.get("name", "N/A")}
[DEBUG]   • Version: {agent_metadata.get("version", "N/A")}
[DEBUG]   • Description: {agent_metadata.get("description", "N/A")}
[DEBUG]   • Category: {agent_metadata.get("category", "N/A")}
[DEBUG]   • Tags: {", ".join(agent_metadata.get("tags", [])) if agent_metadata.get("tags") else "None"}
[DEBUG]   • Model: {agent_metadata.get("details", {}).get("agent", {}).get("defaults", {}).get("model", "N/A")}
[DEBUG]   • Model Provider: {
                        agent_metadata.get("details", {})
                        .get("agent", {})
                        .get("defaults", {})
                        .get("model_provider", "N/A")
                    }
[DEBUG]   • Model Temperature: {
                        agent_metadata.get("details", {})
                        .get("agent", {})
                        .get("defaults", {})
                        .get("model_temperature", "N/A")
                    }
[DEBUG]   • Model Max Tokens: {
                        agent_metadata.get("details", {})
                        .get("agent", {})
                        .get("defaults", {})
                        .get("model_max_tokens", "N/A")
                    }
[DEBUG]   • Show Entry: {agent_metadata.get("show_entry", "N/A")}
[DEBUG]    ----------------------------
"""

                    print(f"\n[DEBUG] Loaded agent from {agent}:\n{agent_info}")
                break

        if not agent_metadata:
            print(f"Missing metadata for {agent}")

        return Agent(
            agent,
            agent_files,
            agent_metadata or {},
            change_to_temp_dir=params.get("change_to_agent_temp_dir", True),
            local_path=path,
        )
    else:
        raise ValueError("Invalid data_source")


def clear_temp_agent_files(agents, verbose=True):
    for agent in agents:
        if agent.temp_dir and os.path.exists(agent.temp_dir):
            if verbose:
                debug_info = f"""[DEBUG] • Removed agent.temp_dir {agent.temp_dir}
[DEBUG]
[DEBUG]  =======================================

"""
                print(debug_info)
            shutil.rmtree(agent.temp_dir)


class EnvironmentRun:
    def __init__(  # noqa: D107
        self,
        near_client: PartialNearClient,
        agents: list[Agent],
        env: Environment,
        thread_id,
        record_run: bool,
        verbose: bool,
    ) -> None:
        self.near_client = near_client
        self.agents = agents
        self.env = env
        self.thread_id = thread_id
        self.record_run = record_run
        self.verbose = verbose

    def __del__(self) -> None:  # noqa: D105
        clear_temp_agent_files(self.agents, verbose=self.verbose)

    def run(self, new_message: str = "", runner_metrics: Optional[RunnerMetrics] = None) -> Optional[str]:  # noqa: D102
        start_time = time.perf_counter()
        self.env.run(new_message, runner_metrics)
        stop_time = time.perf_counter()
        write_metric("ExecuteAgentDuration", stop_time - start_time, verbose=self.verbose)
        return self.thread_id


def start_with_environment(
    agents: str,
    auth: AuthData,
    thread_id,
    run_id,
    additional_path: str = "",
    params: Optional[dict] = None,
    print_system_log: bool = False,
    hub_client: Optional[OpenAI] = None,
) -> EnvironmentRun:
    """Initializes environment for agent runs."""
    params = params or {}
    verbose: bool = params.get("verbose", True)
    if verbose:
        debug_info = f"""

[DEBUG] ==== Running Agent ====

[DEBUG] Agent(s):     {agents}
[DEBUG] Thread ID:    {thread_id}
[DEBUG] Run ID:       {run_id}
[DEBUG] Auth User:    {auth.account_id}
"""
        # Hidden because list of parameters is always the same
        # if params:
        #    debug_info += "\n[DEBUG] Parameters:\n" + "\n".join(f"[DEBUG]   • {key}" for key in params.keys())

        print(debug_info)

    api_url = str(params.get("api_url", DEFAULT_API_URL))
    user_env_vars: dict = params.get("user_env_vars", {}) or {}
    agent_env_vars: dict = params.get("agent_env_vars", {})

    if api_url != DEFAULT_API_URL and verbose:
        print(f"WARNING: Using custom API URL: {api_url}")

    near_client = PartialNearClient(api_url, auth, runner_api_key=protected_vars.get("RUNNER_API_KEY"))

    loaded_agents: list[Agent] = []

    # TODO: Handle the case when multiple agents are provided (comma-separated)
    if "," in agents:
        print("Only a single agent run is supported.")
        agents = agents.split(",")[0]

    for agent_name in agents.split(","):
        agent = load_agent(near_client, agent_name, params, additional_path, verbose=verbose)
        # agents secrets has higher priority then agent metadata's env_vars
        agent.env_vars = {**agent.env_vars, **agent_env_vars.get(agent_name, {})}
        loaded_agents.append(agent)

    # TODO: Handle the case when multiple agents are provided (comma-separated)
    agent = loaded_agents[0]
    # combine agent.env_vars and user_env_vars
    agent_and_user_env_vars = {**agent.env_vars, **user_env_vars}
    # save os env vars
    os.environ.update(agent_and_user_env_vars)
    # save env_vars
    agent.env_vars = agent_and_user_env_vars
    user_env_vars = agent_and_user_env_vars

    if params.get("provider", ""):
        agent.model_provider = params["provider"]
    if params.get("model", ""):
        agent.model = params["model"]
        if not params.get("provider", "") and PROVIDER_MODEL_SEP in agent.model:
            agent.model_provider = ""
    if params.get("temperature", ""):
        agent.model_temperature = params["temperature"]
    if params.get("max_tokens", ""):
        agent.model_max_tokens = params["max_tokens"]
    if verbose:
        print(
            f"[DEBUG] • Agent info: provider: {agent.model_provider} // model: {agent.model} "
            f"// temperature: {agent.model_temperature} // max_tokens: {agent.model_max_tokens}"
        )

    client_config = ClientConfig(
        base_url=api_url + "/v1",
        auth=auth,
    )
    inference_client = InferenceClient(client_config, protected_vars.get("RUNNER_API_KEY"), agent.identifier)

    global provider_models_cache
    global provider_models_cache_time
    # Force a check for new models after an hour if the runner has stayed hot for that long
    # this is a failsafe given usage patterns at the time of writing, if models are uploaded more frequently and
    # runners stay hot, it could be adjusted down or client model caching removed.
    if not provider_models_cache or (time.time() - (provider_models_cache_time or 0) > 3600):
        if provider_models_cache_time:
            write_metric("InferenceClientCacheCleared", "1", "Count")
        provider_models_cache_time = time.time()
        provider_models_cache = inference_client.provider_models
    else:
        inference_client.set_provider_models(provider_models_cache)

    if not hub_client:
        hub_client = client_config.get_hub_client()
    assert hub_client

    env = Environment(
        loaded_agents,
        inference_client,
        hub_client,
        thread_id,
        run_id,
        env_vars=user_env_vars,
        print_system_log=print_system_log,
        agent_runner_user=protected_vars.get("AGENT_RUNNER_USER"),
        fastnear_api_key=protected_vars.get("FASTNEAR_APY_KEY"),
        upload_entry_fn=near_client.upload_new_entry,
    )
    env.add_agent_start_system_log(agent_idx=0)
    return EnvironmentRun(near_client, loaded_agents, env, thread_id, params.get("record_run", True), verbose=verbose)


def run_with_environment(
    agents: str,
    auth: AuthData,
    thread_id,
    run_id,
    additional_path: str = "",
    new_message: str = "",
    params: Optional[dict] = None,
    print_system_log: bool = False,
    runner_metrics: Optional[RunnerMetrics] = None,
    hub_client: Optional[OpenAI] = None,
) -> Optional[str]:
    """Runs agent against environment fetched from id, optionally passing a new message to the environment."""
    environment_run = start_with_environment(
        agents, auth, thread_id, run_id, additional_path, params, print_system_log, hub_client=hub_client
    )
    return environment_run.run(new_message, runner_metrics=runner_metrics)
