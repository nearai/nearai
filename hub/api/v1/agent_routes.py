from typing import Optional

import boto3
from fastapi import APIRouter, Depends, HTTPException
from nearai.clients.lambda_client import LambdaWrapper
from pydantic import BaseModel, Field

from hub.api.v1.auth import AuthToken, revokable_auth

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
        description="A message to pass to the environment before running the agents.",
    )


@v1_router.post("/threads/runs", tags=["Agents", "Assistants"])
@v1_router.post("/environment/runs", tags=["Agents", "Assistants"])
def create_environment_and_run(body: CreateThreadAndRunRequest, auth: AuthToken = Depends(revokable_auth)) -> str:
    """Run an agent against an existing or a new environment.

    Returns the ID of the new environment resulting from the run.
    """
    if not body.agent_id and not body.assistant_id:
        raise HTTPException(status_code=400, detail="Missing required parameters: agent_id or assistant_id")

    agents = body.agent_id or body.assistant_id
    environment_id = body.environment_id or body.thread
    new_message = body.new_message

    wrapper = LambdaWrapper(boto3.client("lambda", region_name="us-east-2"))
    result = wrapper.invoke_function(
        "agent-runner-docker",
        {"agents": agents, "environment_id": environment_id, "auth": auth.json(), "new_message": new_message},
    )
    return result
