from os import getenv
from typing import Any, Dict, Optional

import boto3
from fastapi import APIRouter, Body, Depends, HTTPException, Response
from nearai.clients.lambda_client import LambdaWrapper
from pydantic import BaseModel, Field

from hub.api.v1.auth import AuthToken, revokable_auth
from hub.api.v1.entry_location import EntryLocation
from hub.api.v1.models import RegistryEntry
from hub.api.v1.registry import S3_BUCKET, get

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


@v1_router.post("/threads/runs", tags=["Agents", "Assistants"])  # OpenAI compatibility
@v1_router.post("/agent/runs", tags=["Agents", "Assistants"])
def run_agent(body: CreateThreadAndRunRequest, auth: AuthToken = Depends(revokable_auth)) -> str:
    """Run an agent against an existing or a new environment.

    Returns the ID of the new environment resulting from the run.
    """
    if not body.agent_id and not body.assistant_id:
        raise HTTPException(status_code=400, detail="Missing required parameters: agent_id or assistant_id")

    agents = body.agent_id or body.assistant_id or ""
    environment_id = body.environment_id or body.thread
    new_message = body.new_message

    runner = _runner_for_env()
    agent_api_url = getenv("API_URL", "https://api.near.ai")

    params = {
        "max_iterations": body.max_iterations,
        "record_run": body.record_run,
        "api_url": agent_api_url,
        "tool_resources": body.tool_resources,
        "user_env_vars": body.user_env_vars or {},
    }

    primary_agent = agents.split(",")[0]
    agent_entry = get(EntryLocation.from_str(primary_agent))
    if not agent_entry:
        raise HTTPException(status_code=404, detail=f"Agent '{primary_agent}' not found in the registry.")
    entry_details = agent_entry.details
    agent_details = entry_details.get("agent", {})
    framework = agent_details.get("framework", "base")

    if framework == "prompt":
        raise HTTPException(status_code=400, detail="Prompt only agents are not implemented yet.")
    else:
        function_name = f"{runner}-{framework.lower()}"
        if agent_api_url != "https://api.near.ai":
            print(f"Passing agent API URL: {agent_api_url}")
        print(f"Running function {function_name} with: agents={agents}, environment_id={environment_id}, ")

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
    env = getenv("SERVER_ENVIRONMENT", "local")
    if env == "production":
        return "production-agent-runner"
    else:
        return "staging-agent-runner"
