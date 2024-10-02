import json
from os import getenv
from typing import Any, Dict, Optional

import boto3
import requests
from fastapi import APIRouter, Body, Depends, HTTPException, Response
from nearai.clients.lambda_client import LambdaWrapper
from pydantic import BaseModel, Field

from hub.api.v1.auth import AuthToken, revokable_auth
from hub.api.v1.entry_location import EntryLocation
from hub.api.v1.models import RegistryEntry
from hub.api.v1.registry import S3_BUCKET, get
from hub.api.v1.sql import SqlClient

s3 = boto3.client("s3")

v1_router = APIRouter(
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
    thread: Optional[str] = Field(
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


def invoke_function_via_curl(runner_invoke_url, agents, environment_id, auth: AuthToken, new_message, params):
    auth_data = auth.model_dump()

    if auth_data["nonce"]:
        if isinstance(auth_data["nonce"], bytes):
            auth_data["nonce"] = auth_data["nonce"].decode("utf-8")

    payload = {
        "agents": agents,
        "environment_id": environment_id,
        "auth": auth_data,
        "new_message": new_message,
        "params": params,
    }

    headers = {"Content-Type": "application/json"}

    response = requests.post(runner_invoke_url, data=json.dumps(payload), headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Request failed with status code {response.status_code}: {response.text}")


def invoke_function_via_lambda(function_name, agents, environment_id, auth: AuthToken, new_message, params):
    wrapper = LambdaWrapper(boto3.client("lambda", region_name="us-east-2"))
    result = wrapper.invoke_function(
        function_name,
        {
            "agents": agents,
            "environment_id": environment_id,
            "auth": auth.model_dump(),
            "new_message": new_message,
            "params": params,
        },
    )

    return result


@v1_router.post("/threads/runs", tags=["Agents", "Assistants"])  # OpenAI compatibility
@v1_router.post("/agent/runs", tags=["Agents", "Assistants"])
def run_agent(body: CreateThreadAndRunRequest, auth: AuthToken = Depends(revokable_auth)) -> str:
    """Run an agent against an existing or a new environment.

    Returns the ID of the new environment resulting from the run.
    """
    if not body.agent_id and not body.assistant_id:
        raise HTTPException(status_code=400, detail="Missing required parameters: agent_id or assistant_id")

    db = SqlClient()

    agents = body.agent_id or body.assistant_id or ""
    environment_id = body.environment_id or body.thread
    new_message = body.new_message

    runner = _runner_for_env()
    agent_api_url = getenv("API_URL", "https://api.near.ai")

    agent_env_vars: Dict[str, Any] = {}
    user_env_vars = body.user_env_vars or {}

    agent_entry: RegistryEntry | None = None
    for agent in reversed(agents.split(",")):
        agent_entry = get(EntryLocation.from_str(agent))

        # read secret for every requested agent
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
    }

    # agent_entry here is the primary agent, because of the reversed loop for all agents
    if not agent_entry:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_entry}' not found in the registry.")

    entry_details = agent_entry.details
    agent_details = entry_details.get("agent", {})
    framework = agent_details.get("framework", "base")

    if framework == "prompt":
        raise HTTPException(status_code=400, detail="Prompt only agents are not implemented yet.")
    else:
        if runner == "local":
            runner_invoke_url = getenv("RUNNER_INVOKE_URL", None)
            if runner_invoke_url:
                return invoke_function_via_curl(runner_invoke_url, agents, environment_id, auth, new_message, params)
        else:
            function_name = f"{runner}-{framework.lower()}"
            if agent_api_url != "https://api.near.ai":
                print(f"Passing agent API URL: {agent_api_url}")
            print(f"Running function {function_name} with: agents={agents}, environment_id={environment_id}, ")

            return invoke_function_via_lambda(function_name, agents, environment_id, auth, new_message, params)

        raise HTTPException(status_code=400, detail="Invalid runner parameters")


@v1_router.post(
    "/download_environment",
    responses={200: {"content": {"application/gzip": {"schema": {"type": "string", "format": "binary"}}}}},
)
def download_environment(entry: RegistryEntry = Depends(get), path: str = Body()):
    assert isinstance(S3_BUCKET, str)
    file = s3.get_object(Bucket=S3_BUCKET, Key=entry.get_key(path))
    headers = {"Content-Disposition": "attachment; filename=environment.tar.gz"}
    return Response(file["Body"].read(), headers=headers, media_type="application/gzip")


def _runner_for_env():
    runner_env = getenv("RUNNER_ENVIRONMENT", "local")
    if runner_env == "production":
        return "production-agent-runner"
    elif runner_env == "staging":
        return "staging-agent-runner"
    else:
        return runner_env
