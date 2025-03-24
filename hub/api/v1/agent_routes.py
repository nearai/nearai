import json
import logging
from collections import deque
from os import getenv
from typing import Any, Dict, List, Optional, Union

import boto3
import requests
from botocore.config import Config
from fastapi import APIRouter, Depends, HTTPException
from nearai.agents.local_runner import LocalRunner
from nearai.clients.lambda_client import LambdaWrapper
from nearai.shared.auth_data import AuthData
from nearai.shared.client_config import DEFAULT_TIMEOUT
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, inspect, text

from hub.api.v1.auth import AuthToken, get_auth
from hub.api.v1.entry_location import EntryLocation
from hub.api.v1.models import Message as MessageModel
from hub.api.v1.models import RegistryEntry, get_session
from hub.api.v1.models import Run as RunModel
from hub.api.v1.models import Thread as ThreadModel
from hub.api.v1.registry import get
from hub.api.v1.sql import SqlClient

S3_ENDPOINT = getenv("S3_ENDPOINT")
s3 = boto3.client(
    "s3",
    endpoint_url=S3_ENDPOINT,
)

run_agent_router = APIRouter(
    tags=["agents, assistants"],
)


class CreateThreadAndRunRequest(BaseModel):
    agent_id: Optional[str] = Field(
        None,
        description="The name or identifier of the agent to use to execute this run. Either `agent_id` or "
        "`assistant_id` must be provided.",
    )
    assistant_id: Optional[str] = Field(
        None,
        description="An OpenAI compatibility alias for agent. The ID of the [assistant](/docs/api-reference/assistants)"
        " to use to execute this run.",
    )
    thread_id: Optional[str] = Field(
        None,
        description="The thread to write messages to. If no thread is provided, an empty thread will be created.",
    )
    new_message: Optional[str] = Field(
        None,
        description="A message to add to the thread before running the agents.",
    )
    max_iterations: Optional[int] = Field(
        10,
        description="Allow an agent to run for up to this number of iterations.",
    )
    record_run: Optional[bool] = Field(
        True,
        description="Whether to record the run in the registry.",
    )
    tool_resources: Optional[Dict[str, Any]] = Field(
        None,
        description="A dictionary of tool resources to use for the run.",
    )
    user_env_vars: Optional[Dict[str, Any]] = Field(
        None,
        description="Env vars provided by the user",
    )


available_local_runners_ports = getenv("AVAILABLE_LOCAL_RUNNER_PORTS", "")
available_local_runners = deque(
    [int(port) for port in available_local_runners_ports.split(",") if port.strip().isdigit()]
)  # Queue of available ports
agent_runners_ports: dict[str, int] = {}  # Mapping of agents to their assigned ports


def invoke_agent_via_url(custom_runner_url, agents, thread_id, run_id, auth: AuthToken, params):
    auth_data = auth.model_dump()

    if auth_data["nonce"]:
        if isinstance(auth_data["nonce"], bytes):
            auth_data["nonce"] = auth_data["nonce"].decode("utf-8")

    if "%PORT%" in custom_runner_url:
        # Assign a port to the agent if not already assigned
        if agents in agent_runners_ports:
            port = agent_runners_ports[agents]  # Reuse existing port
        elif available_local_runners:
            port = available_local_runners.popleft()  # Assign a free port
            agent_runners_ports[agents] = port
        else:
            # If no ports are available, reassign the oldest used agent's port
            oldest_agent = next(iter(agent_runners_ports))
            logging.warning(f"No available local runners ports! Reassigning port from agent {oldest_agent}")
            port = agent_runners_ports[oldest_agent]
            agent_runners_ports[agents] = port  # Update mapping

        custom_runner_url = custom_runner_url.replace("%PORT%", str(port))

    payload = {
        "agents": agents,
        "thread_id": thread_id,
        "run_id": run_id,
        "auth": auth_data,
        "params": params,
    }

    headers = {"Content-Type": "application/json"}

    response = requests.post(custom_runner_url, data=json.dumps(payload), headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Request failed with status code {response.status_code}: {response.text}")


def invoke_agent_via_lambda(function_name, agents, thread_id, run_id, auth: AuthToken, params):
    config = Config(read_timeout=DEFAULT_TIMEOUT, connect_timeout=DEFAULT_TIMEOUT, retries=None)
    wrapper = LambdaWrapper(boto3.client("lambda", region_name="us-east-2", config=config), thread_id, run_id)
    auth_data = auth.model_dump()

    if auth_data["nonce"]:
        if isinstance(auth_data["nonce"], bytes):
            auth_data["nonce"] = auth_data["nonce"].decode("utf-8")

    result = wrapper.invoke_function(
        function_name,
        {
            "agents": agents,
            "thread_id": thread_id,
            "run_id": run_id,
            "auth": auth_data,
            "params": params,
        },
    )

    return result


@run_agent_router.post("/threads/runs", tags=["Agents", "Assistants"])  # OpenAI compatibility
@run_agent_router.post("/agent/runs", tags=["Agents", "Assistants"])
def run_agent(body: CreateThreadAndRunRequest, auth: AuthToken = Depends(get_auth)) -> str:
    """Run an agent against an existing or a new thread.

    Returns the ID of the new thread resulting from the run.
    """
    if not body.agent_id and not body.assistant_id:
        raise HTTPException(status_code=400, detail="Missing required parameters: agent_id or assistant_id")

    db = SqlClient()

    agents = body.agent_id or body.assistant_id or ""
    thread_id = body.thread_id
    if thread_id:
        with get_session() as session:
            thread = session.get(ThreadModel, thread_id)
            if thread is None:
                raise HTTPException(status_code=404, detail="Thread not found")
            if thread.owner_id != auth.account_id:
                raise HTTPException(
                    status_code=403, detail="You don't have permission to access messages from this thread"
                )

    new_message = body.new_message

    runner = _runner_for_env()
    agent_api_url = getenv("API_URL", "https://api.near.ai")
    data_source = getenv("DATA_SOURCE", "registry")

    agent_env_vars: Dict[str, Any] = {}
    user_env_vars = body.user_env_vars or {}

    agent_entry: Union[RegistryEntry, None] = None
    for agent in reversed(agents.split(",")):
        agent_entry = get_agent_entry(agent, data_source)

        # read secret for every requested agent
        if agent_entry:
            (agent_secrets, user_secrets) = db.get_agent_secrets(
                auth.account_id, agent_entry.namespace, agent_entry.name, agent_entry.version
            )

            # agent vars from metadata has lower priority then agent secret
            agent_env_vars[agent] = {**(agent_env_vars.get(agent, {})), **agent_secrets}

            # user vars from url has higher priority then user secret
            user_env_vars = {**user_secrets, **user_env_vars}

    params = {
        "max_iterations": body.max_iterations,
        "record_run": body.record_run,
        "api_url": agent_api_url,
        "tool_resources": body.tool_resources,
        "user_env_vars": user_env_vars,
        "agent_env_vars": agent_env_vars,
        "data_source": data_source,
    }

    if not agent_entry:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_entry}' not found in the registry.")

    specific_agent_version_to_run = f"{agent_entry.namespace}/{agent_entry.name}/{agent_entry.version}"
    framework = agent_entry.get_framework()

    with get_session() as session:
        if not thread_id:
            thread_model = ThreadModel(
                owner_id=auth.account_id,
                meta_data={
                    "agent_ids": [agents],
                },
            )
            session.add(thread_model)
            session.commit()
            thread_id = thread_model.id

        run_model = RunModel(
            thread_id=thread_id,
            assistant_id=agents,  # needs primary agent
            model="agent_specified",
            status="queued",
        )

        if new_message:
            message_model = MessageModel(thread_id=thread_id, content=new_message, role="user", run_id=run_model.id)
            session.add(message_model)
            session.commit()

    session.add(run_model)
    session.commit()

    run_id = run_model.id

    if framework == "prompt":
        raise HTTPException(status_code=400, detail="Prompt only agents are not implemented yet.")

    if runner == "custom_runner":
        custom_runner_url = getenv("CUSTOM_RUNNER_URL", None)
        if custom_runner_url:
            invoke_agent_via_url(custom_runner_url, specific_agent_version_to_run, thread_id, run_id, auth, params)
    elif runner == "local_runner":
        """Runs agents directly from the local machine."""

        LocalRunner(
            None,
            agents,
            thread_id,
            run_id,
            AuthData(**auth.model_dump()),  # TODO: https://github.com/nearai/nearai/issues/421
            params,
        )
    else:
        function_name = f"{runner}-{framework.lower()}"
        if agent_api_url != "https://api.near.ai":
            print(f"Passing agent API URL: {agent_api_url}")

        invoke_agent_via_lambda(function_name, specific_agent_version_to_run, thread_id, run_id, auth, params)

    with get_session() as session:
        completed_run_model = session.get(RunModel, run_id)
        if completed_run_model:
            completed_run_model.status = "requires_action"
            session.commit()

    return thread_id


def _runner_for_env():
    runner_env = getenv("RUNNER_ENVIRONMENT", "local_runner")
    if runner_env == "production":
        return "production-agent-runner"
    elif runner_env == "staging":
        return "staging-agent-runner"
    else:
        return runner_env


def get_agent_entry(agent, data_source: str) -> Optional[RegistryEntry]:
    if data_source == "registry":
        return get(EntryLocation.from_str(agent))
    elif data_source == "local_files":
        entry_location = EntryLocation.from_str(agent)
        return RegistryEntry(
            namespace=entry_location.namespace,
            name=entry_location.name,
            version=entry_location.version,
        )
    else:
        raise HTTPException(status_code=404, detail=f"Illegal data_source '{data_source}'.")


class FilterAgentsRequest(BaseModel):
    owner_id: Optional[str]
    with_capabilities: Optional[bool] = False
    latest_versions_only: Optional[bool] = True
    limit: Optional[int] = 100
    offset: Optional[int] = 0


@run_agent_router.post("/find_agents", response_model=List[RegistryEntry])
def find_agents(request_data: FilterAgentsRequest, auth: AuthToken = Depends(get_auth)) -> List[RegistryEntry]:
    """Find agents based on various parameters."""
    with get_session() as session:
        # Start building the base query
        query = session.query(RegistryEntry)

        # Get the column for the namespace. This helps mypy to understand the type of the column
        # inspect uses cached data, so it's not a performance issue, but this can be optimized
        # by storing the mapper in a variable and reusing it
        mapper = inspect(RegistryEntry)

        category_column = mapper.columns["category"]
        namespace_column = mapper.columns["namespace"]
        name_column = mapper.columns["name"]
        version_column = mapper.columns["version"]

        query = query.filter(category_column == "agent")

        # Filter by latest versions only (if flag is set)
        if request_data.latest_versions_only:
            latest_versions = (
                session.query(namespace_column, name_column, func.max(version_column).label("max_version"))
                .group_by(namespace_column, name_column)
                .subquery()
            )

            # Join the main query with the subquery to get only the latest versions
            query = query.join(
                latest_versions,
                and_(
                    namespace_column == latest_versions.c.namespace,
                    name_column == latest_versions.c.name,
                    version_column == latest_versions.c.max_version,
                ),
            )

        # Filter by owner (if flag is set)
        if request_data.owner_id is not None:
            namespace_column = mapper.columns["namespace"]
            query = query.filter(namespace_column == request_data.owner_id)

        # Filter by capabilities (if flag is set)
        if request_data.with_capabilities:
            query = query.filter(text("JSON_EXTRACT_JSON(details, 'capabilities') IS NOT NULL"))

        # Limit and offset
        query = query.limit(request_data.limit).offset(request_data.offset)

        # Execute query and return results
        filtered_agents = query.all()

        return filtered_agents
