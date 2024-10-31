import json
from os import getenv
from typing import Any, Dict, Optional, Union

import boto3
import requests
from fastapi import APIRouter, Body, Depends, HTTPException, Response
from nearai.agents.local_runner import LocalRunner
from nearai.clients.lambda_client import LambdaWrapper
from pydantic import BaseModel, Field
from shared.auth_data import AuthData

from hub.api.v1.auth import AuthToken, revokable_auth
from hub.api.v1.entry_location import EntryLocation
from hub.api.v1.models import Message as MessageModel
from hub.api.v1.models import RegistryEntry, get_session
from hub.api.v1.models import Run as RunModel
from hub.api.v1.models import Thread as ThreadModel
from hub.api.v1.registry import S3_BUCKET, get
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
    environment_id: Optional[str] = Field(
        None,
        description="The ID of the environment to use to as a base for this run. If not provided, a new environment"
        " will be created.",
    )
    thread_id: Optional[str] = Field(
        None,
        description="An OpenAI compatibility alias for environment. If no thread is provided, an empty thread"
        " will be created.",
    )
    new_message: Optional[str] = Field(
        None,
        description="A message to add to the environment chat.txt before running the agents.",
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


def invoke_agent_via_url(custom_runner_url, agents, thread_id, run_id, auth: AuthToken, new_message, params):
    auth_data = auth.model_dump()

    if auth_data["nonce"]:
        if isinstance(auth_data["nonce"], bytes):
            auth_data["nonce"] = auth_data["nonce"].decode("utf-8")

    payload = {
        "agents": agents,
        "thread_id": thread_id,
        "run_id": run_id,
        "auth": auth_data,
        "new_message": new_message,
        "params": params,
    }

    headers = {"Content-Type": "application/json"}

    response = requests.post(custom_runner_url, data=json.dumps(payload), headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Request failed with status code {response.status_code}: {response.text}")


def invoke_agent_via_lambda(function_name, agents, thread_id, run_id, auth: AuthToken, new_message, params):
    wrapper = LambdaWrapper(boto3.client("lambda", region_name="us-east-2"))
    result = wrapper.invoke_function(
        function_name,
        {
            "agents": agents,
            "thread_id": thread_id,
            "run_id": run_id,
            "auth": auth.model_dump(),
            "new_message": new_message,
            "params": params,
        },
    )

    return result


@run_agent_router.post("/threads/runs", tags=["Agents", "Assistants"])  # OpenAI compatibility
@run_agent_router.post("/agent/runs", tags=["Agents", "Assistants"])
def run_agent(body: CreateThreadAndRunRequest, auth: AuthToken = Depends(revokable_auth)) -> str:
    """Run an agent against an existing or a new environment.

    Returns the ID of the new environment resulting from the run.
    """
    if not body.agent_id and not body.assistant_id:
        raise HTTPException(status_code=400, detail="Missing required parameters: agent_id or assistant_id")

    db = SqlClient()

    agents = body.agent_id or body.assistant_id or ""
    thread_id = body.environment_id or body.thread_id
    new_message = body.new_message

    runner = _runner_for_env()
    agent_api_url = getenv("API_URL", "https://api.near.ai")
    data_source = getenv("DATA_SOURCE", "registry")

    agent_env_vars: Dict[str, Any] = {}
    user_env_vars = body.user_env_vars or {}

    agent_entry: Union[RegistryEntry, None] = None
    for agent in reversed(agents.split(",")):
        agent_entry = get_agent_entry(agent, data_source, auth.account_id)

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

    entry_details = agent_entry.details
    agent_details = entry_details.get("agent", {})
    framework = agent_details.get("framework", "base")

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
    else:
        if runner == "custom_runner":
            custom_runner_url = getenv("CUSTOM_RUNNER_URL", None)
            if custom_runner_url:
                invoke_agent_via_url(custom_runner_url, agents, thread_id, run_id, auth, new_message, params)
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

            invoke_agent_via_lambda(function_name, agents, thread_id, run_id, auth, new_message, params)

    with get_session() as session:
        completed_run_model = session.get(RunModel, run_id)
        if completed_run_model:
            completed_run_model.status = "requires_action"
            session.commit()

    return thread_id


@run_agent_router.post(
    "/download_environment",
    responses={200: {"content": {"application/gzip": {"schema": {"type": "string", "format": "binary"}}}}},
)
def download_environment(entry: RegistryEntry = Depends(get), path: str = Body()):
    assert isinstance(S3_BUCKET, str)
    file = s3.get_object(Bucket=S3_BUCKET, Key=entry.get_key(path))
    headers = {"Content-Disposition": "attachment; filename=environment.tar.gz"}
    return Response(file["Body"].read(), headers=headers, media_type="application/gzip")


def _runner_for_env():
    runner_env = getenv("RUNNER_ENVIRONMENT", "local_runner")
    if runner_env == "production":
        return "production-agent-runner"
    elif runner_env == "staging":
        return "staging-agent-runner"
    else:
        return runner_env


def get_agent_entry(agent, data_source: str, account_id: str) -> Union[RegistryEntry, None]:
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
