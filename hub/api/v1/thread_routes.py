import logging
from datetime import datetime
from os import getenv
from typing import List, Literal

import boto3
from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Path, Query
from openai.types.beta.thread import Thread
from openai.types.beta.thread_create_params import ThreadCreateParams
from openai.types.beta.threads.message import Message
from openai.types.beta.threads.message_create_params import MessageCreateParams
from openai.types.beta.threads.message_list_params import MessageListParams
from openai.types.beta.threads.message_update_params import MessageUpdateParams
from openai.types.beta.threads.run import Run as OpenAIRun
from openai.types.beta.threads.run_create_params import RunCreateParams
from pydantic import BaseModel
from sqlmodel import select

from hub.api.v1.agent_routes import _runner_for_env, invoke_function_via_curl, invoke_function_via_lambda
from hub.api.v1.auth import AuthToken, revokable_auth
from hub.api.v1.models import Message as MessageModel
from hub.api.v1.models import Run as RunModel
from hub.api.v1.models import Thread as ThreadModel
from hub.api.v1.models import get_session

s3 = boto3.client("s3")

threads_router = APIRouter(
    tags=["Threads"],
)

logger = logging.getLogger(__name__)


@threads_router.post("/threads")
async def create_thread(
    thread: ThreadCreateParams = Body(...),
    auth: AuthToken = Depends(revokable_auth),
) -> Thread:
    with get_session() as session:
        print(thread)
        thread_model = ThreadModel(
            messages=thread.messages if hasattr(thread, "messages") else [],
            meta_data=thread.metadata if hasattr(thread, "metadata") else None,
            tool_resources=thread.tool_resources if hasattr(thread, "tool_resources") else None,
        )
        session.add(thread_model)
        session.commit()
        return thread_model.to_openai()


@threads_router.get("/threads/{thread_id}")
async def get_thread(
    thread_id: str,
    auth: AuthToken = Depends(revokable_auth),
) -> Thread:
    with get_session() as session:
        thread_model = session.get(ThreadModel, thread_id)
        if thread_model is None:
            raise HTTPException(status_code=404, detail="Thread not found")
        return thread_model.to_openai()


@threads_router.post("/threads/{thread_id}/messages")
async def create_message(
    thread_id: str,
    message: MessageCreateParams = Body(...),
    auth: AuthToken = Depends(revokable_auth),
) -> Message:
    with get_session() as session:
        thread_model = session.get(ThreadModel, thread_id)
        if thread_model is None:
            raise HTTPException(status_code=404, detail="Thread not found")

        content = message["content"]
        if isinstance(content, str):
            content = [{"type": "text", "text": {"value": content, "annotations": []}}]
        elif isinstance(content, list):
            content = [
                {"type": "text", "text": {"value": item["text"]["value"], "annotations": []}}
                for item in content
                if item["type"] == "text"
            ]

        message_model = MessageModel(
            thread_id=thread_id,
            content=content,
            role=message["role"],
        )
        session.add(message_model)
        session.commit()
        return message_model.to_openai()


class ListMessagesResponse(BaseModel):
    object: Literal["list"]
    data: List[Message]
    has_more: bool
    first_id: str
    last_id: str


@threads_router.get("/threads/{thread_id}/messages")
async def list_messages(
    thread_id: str,
    after: str = Query(
        None, description="A cursor for use in pagination. `after` is an object ID that defines your place in the list."
    ),
    before: str = Query(
        None,
        description="A cursor for use in pagination. `before` is an object ID that defines your place in the list.",
    ),
    limit: int = Query(
        20, description="A limit on the number of objects to be returned. Limit can range between 1 and 100."
    ),
    order: Literal["asc", "desc"] = Query(
        "desc", description="Sort order by the `created_at` timestamp of the objects."
    ),
    run_id: str = Query(None, description="Filter messages by the run ID that generated them."),
    auth: AuthToken = Depends(revokable_auth),
) -> ListMessagesResponse:
    logger.info(f"Listing messages for thread: {thread_id}")
    with get_session() as session:
        statement = select(MessageModel).where(MessageModel.thread_id == thread_id)

        # Apply filters
        if after:
            after_message = session.get(MessageModel, after)
            if after_message:
                statement = statement.where(MessageModel.created_at > after_message.created_at)

        if run_id:
            statement = statement.where(MessageModel.run_id == run_id)

        # Apply limit
        statement = statement.limit(limit)

        messages = session.exec(statement).all()
        logger.info(
            f"Found {len(messages)} messages with filter: after={after}, run_id={run_id}, limit={limit}, order={order}"
        )

        # Determine if there are more messages
        has_more = len(messages) == limit

        if messages:
            first_id = messages[0].id
            last_id = messages[-1].id
        else:
            first_id = last_id = None

        return ListMessagesResponse(
            object="list",
            data=[message.to_openai() for message in messages],
            has_more=has_more,
            first_id=first_id or "",
            last_id=last_id or "",
        )


@threads_router.patch("/threads/{thread_id}/messages/{message_id}")
async def modify_message(
    thread_id: str,
    message_id: str,
    message: MessageUpdateParams = Body(...),
    auth: AuthToken = Depends(revokable_auth),
) -> Message:
    with get_session() as session:
        message_model = session.get(MessageModel, message_id)
        if message_model is None:
            raise HTTPException(status_code=404, detail="Message not found")
        message_model.meta_data = message["metadata"] if isinstance(message["metadata"], dict) else None
        session.commit()
        return message_model.to_openai()


@threads_router.post("/threads/{thread_id}/runs")
async def create_run(
    thread_id: str,
    background_tasks: BackgroundTasks,
    run: RunCreateParams = Body(...),
    auth: AuthToken = Depends(revokable_auth),
) -> OpenAIRun:
    logger.info(f"Creating run for thread: {thread_id}")
    with get_session() as session:
        thread_model = session.get(ThreadModel, thread_id)
        if thread_model is None:
            raise HTTPException(status_code=404, detail="Thread not found")
        run_model = RunModel(
            thread_id=thread_id,
            **run,
        )
        background_tasks.add_task(run_agent, thread_id, run_model.id, auth)

        session.add(run_model)
        session.commit()
        return run_model.to_openai()


def run_agent(thread_id: str, run_id: str, auth: AuthToken = Depends(revokable_auth)) -> OpenAIRun:
    """Task to run an agent in the background."""
    print("HERE run_agent")
    with get_session() as session:
        run_model = session.get(RunModel, run_id)
        if run_model is None:
            raise HTTPException(status_code=404, detail="Run not found")
        # TODO: secrets
        agent_api_url = getenv("API_URL", "https://api.near.ai")

        params = {
            "max_iterations": 3,
            "record_run": True,
            "api_url": agent_api_url,
            "tool_resources": run_model.tools,
            "user_env_vars": {},
            "agent_env_vars": {},
            "data_source": "registry",
        }
        agents = run_model.assistant_id
        runner = _runner_for_env()
        framework = "base"

        if runner == "local":
            runner_invoke_url = getenv("RUNNER_INVOKE_URL", None)
            if runner_invoke_url:
                invoke_function_via_curl(runner_invoke_url, agents, thread_id, auth, "", params)
            else:
                raise HTTPException(status_code=400, detail="Runner invoke URL not set for local runner")
        else:
            function_name = f"{runner}-{framework.lower()}"
            if agent_api_url != "https://api.near.ai":
                print(f"Passing agent API URL: {agent_api_url}")
            print(
                f"Running function {function_name} with: assistant_id={run_model.assistant_id}, thread_id={thread_id}, run_id={run_id}"
            )
            invoke_function_via_lambda(function_name, agents, thread_id, auth, "", params)

        run_model.completed_at = datetime.now()
        run_model.status = "completed"

        session.add(run_model)
        session.commit()

        return run_model.to_openai()


@threads_router.get("/threads/{thread_id}/runs/{run_id}")
async def get_run(
    thread_id: str = Path(..., description="The ID of the thread"),
    run_id: str = Path(..., description="The ID of the run"),
    auth: AuthToken = Depends(revokable_auth),
) -> OpenAIRun:
    """Get details of a specific run for a thread."""
    with get_session() as session:
        run_model = session.get(RunModel, run_id)
        if run_model is None:
            raise HTTPException(status_code=404, detail="Run not found")

        if run_model.thread_id != thread_id:
            raise HTTPException(status_code=404, detail="Run not found for this thread")

        return run_model.to_openai()
