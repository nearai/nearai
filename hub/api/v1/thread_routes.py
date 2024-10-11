import logging
from datetime import datetime
from os import getenv
from typing import Any, Dict, Iterable, List, Literal, Optional, Union

import boto3
from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Path, Query
from openai.types.beta.assistant_response_format_option_param import AssistantResponseFormatOptionParam
from openai.types.beta.thread import Thread
from openai.types.beta.thread_create_params import ThreadCreateParams
from openai.types.beta.threads.message import Attachment, Message
from openai.types.beta.threads.message_create_params import MessageContentPartParam
from openai.types.beta.threads.message_update_params import MessageUpdateParams
from openai.types.beta.threads.run import Run as OpenAIRun
from openai.types.beta.threads.run_create_params import AdditionalMessage, TruncationStrategy
from openai.types.beta.threads.runs.run_step_include import RunStepInclude
from pydantic import BaseModel, Field
from sqlmodel import select

from hub.api.v1.agent_routes import (
    _runner_for_env,
    get_agent_entry,
    invoke_function_via_curl,
    invoke_function_via_lambda,
)
from hub.api.v1.auth import AuthToken, revokable_auth
from hub.api.v1.models import Message as MessageModel
from hub.api.v1.models import Run as RunModel
from hub.api.v1.models import Thread as ThreadModel
from hub.api.v1.models import get_session
from hub.api.v1.sql import SqlClient

s3 = boto3.client("s3")

threads_router = APIRouter(
    tags=["Threads"],
)

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "fireworks::llama-v3p1-70b-instruct"


@threads_router.post("/threads")
async def create_thread(
    thread: ThreadCreateParams = Body(...),
    auth: AuthToken = Depends(revokable_auth),
) -> Thread:
    with get_session() as session:
        print(thread)
        thread_model = ThreadModel(
            messages=thread["messages"] if hasattr(thread, "messages") else [],
            meta_data=thread["metadata"] if hasattr(thread, "metadata") else None,
            tool_resources=thread["tool_resources"] if hasattr(thread, "tool_resources") else None,
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


class MessageCreateParams(BaseModel):
    content: Union[str, Iterable[MessageContentPartParam]]
    """The text contents of the message."""

    role: Literal["user", "assistant", "agent", "system"]
    """The role of the entity that is creating the message. Allowed values include:

    - `user`: Indicates the message is sent by an actual user and should be used in
      most cases to represent user-generated messages.
    - `assistant`: Indicates the message is generated by the assistant. Use this
      value to insert messages from the assistant into the conversation.
    - `agent`: Similar to `assistant`.
    - `system`: Indicates the message is a system message, such as a tool call.
    """

    attachments: Optional[Iterable[Attachment]] = None
    """A list of files attached to the message, and the tools they should be added to."""

    metadata: Optional[dict[str, str]] = None
    """Set of 16 key-value pairs that can be attached to an object.

    This can be useful for storing additional information about the object in a
    structured format. Keys can be a maximum of 64 characters long and values can be
    a maximum of 512 characters long.
    """

    assistant_id: Optional[str] = None
    """The ID of the assistant creating the message."""


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

        content = message.content
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
            role=message.role,
            assistant_id=message.assistant_id,
            meta_data=message.metadata,
            attachments=message.attachments,
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
            first_id = last_id = ""

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


class RunCreateParamsBase(BaseModel):
    assistant_id: str = Field(..., description="The ID of the assistant to use to execute this run.")
    model: Optional[str] = Field(
        default=DEFAULT_MODEL, description="The ID of the Model to be used to execute this run."
    )
    instructions: Optional[str] = Field(
        None,
        description="Overrides the instructions of the assistant. This is useful for modifying the behavior on a per-run basis.",
    )
    tools: Optional[List[dict]] = Field(None, description="Override the tools the assistant can use for this run.")
    metadata: Optional[dict] = Field(None, description="Set of 16 key-value pairs that can be attached to an object.")

    include: List[RunStepInclude] = Field(None, description="A list of additional fields to include in the response.")
    additional_instructions: Optional[str] = Field(
        None, description="Appends additional instructions at the end of the instructions for the run."
    )
    additional_messages: Optional[List[AdditionalMessage]] = Field(
        None, description="Adds additional messages to the thread before creating the run."
    )
    max_completion_tokens: Optional[int] = Field(
        None, description="The maximum number of completion tokens that may be used over the course of the run."
    )
    max_prompt_tokens: Optional[int] = Field(
        None, description="The maximum number of prompt tokens that may be used over the course of the run."
    )
    parallel_tool_calls: Optional[bool] = Field(
        None, description="Whether to enable parallel function calling during tool use."
    )
    response_format: Optional[AssistantResponseFormatOptionParam] = Field(
        None, description="Specifies the format that the model must output."
    )
    temperature: Optional[float] = Field(None, description="What sampling temperature to use, between 0 and 2.")
    tool_choice: Optional[Union[str, dict]] = Field(
        None, description="Controls which (if any) tool is called by the model."
    )
    top_p: Optional[float] = Field(
        None, description="An alternative to sampling with temperature, called nucleus sampling."
    )
    truncation_strategy: Optional[TruncationStrategy] = Field(
        None, description="Controls for how a thread will be truncated prior to the run."
    )
    stream: bool = Field(False, description="Whether to stream the run.")

    # Custom fields
    schedule_at: Optional[datetime] = Field(None, description="The time at which the run should be scheduled.")


@threads_router.post("/threads/{thread_id}/runs")
async def create_run(
    thread_id: str,
    background_tasks: BackgroundTasks,
    run: RunCreateParamsBase = Body(...),
    auth: AuthToken = Depends(revokable_auth),
) -> OpenAIRun:
    logger.info(f"Creating run for thread: {thread_id}")
    with get_session() as session:
        thread_model = session.get(ThreadModel, thread_id)
        if thread_model is None:
            raise HTTPException(status_code=404, detail="Thread not found")

        if run.additional_messages:
            messages = []
            for message in run.additional_messages:
                messages.append(
                    MessageModel(
                        thread_id=thread_id,
                        content=[{"type": "text", "text": {"value": message["content"], "annotations": []}}],
                        role=message["role"],
                        attachments=message["attachments"] if "attachments" in message else None,
                        meta_data=message["metadata"] if "metadata" in message else None,
                    )
                )
            session.add_all(messages)

        run_model = RunModel(
            thread_id=thread_id,
            assistant_id=run.assistant_id,
            model=run.model,
            instructions=run.instructions,
            tools=run.tools,
            metadata=run.metadata,
            include=run.include,
            additional_instructions=run.additional_instructions,
            additional_messages=run.additional_messages,
            max_completion_tokens=run.max_completion_tokens,
            max_prompt_tokens=run.max_prompt_tokens,
            parallel_tool_calls=run.parallel_tool_calls,
            response_format=run.response_format,
            temperature=run.temperature,
            tool_choice=run.tool_choice,
            top_p=run.top_p,
            truncation_strategy=run.truncation_strategy,
        )

        session.add(run_model)

        # Add the run and messages in DB
        session.commit()

        # Queue the run
        background_tasks.add_task(run_agent, thread_id, run_model.id, auth)

        return run_model.to_openai()


def run_agent(thread_id: str, run_id: str, auth: AuthToken = Depends(revokable_auth)) -> OpenAIRun:
    """Task to run an agent in the background."""
    with get_session() as session:
        run_model = session.get(RunModel, run_id)
        if run_model is None:
            raise HTTPException(status_code=404, detail="Run not found")

        agent_api_url = getenv("API_URL", "https://api.near.ai")
        data_source = getenv("DATA_SOURCE", "registry")

        agent_env_vars: Dict[str, Any] = {}
        user_env_vars: Dict[str, Any] = {}

        agent_entry = get_agent_entry(run_model.assistant_id, data_source)

        # read secret for every requested agent
        if agent_entry:
            db = SqlClient()

            (agent_secrets, user_secrets) = db.get_agent_secrets(
                auth.account_id, agent_entry.namespace, agent_entry.name, agent_entry.version
            )

            # agent vars from metadata has lower priority then agent secret
            agent_env_vars[run_model.assistant_id] = {
                **(agent_env_vars.get(run_model.assistant_id, {})),
                **agent_secrets,
            }

            # user vars from url has higher priority then user secret
            user_env_vars = {**user_secrets, **user_env_vars}

        params = {
            "max_iterations": 3,
            "record_run": True,
            "api_url": agent_api_url,
            "tool_resources": run_model.tools,
            "data_source": data_source,
            "model": run_model.model,
            "user_env_vars": user_env_vars,
            "agent_env_vars": agent_env_vars,
        }
        agents = run_model.assistant_id
        runner = _runner_for_env()

        framework = "base"
        if agent_entry and "agent" in agent_entry.details:
            framework = agent_entry.details["agent"].get("framework", "base")

        if runner == "local":
            runner_invoke_url = getenv("RUNNER_INVOKE_URL", None)
            if runner_invoke_url:
                invoke_function_via_curl(runner_invoke_url, agents, thread_id, run_id, auth, "", params)
            else:
                raise HTTPException(status_code=400, detail="Runner invoke URL not set for local runner")
        else:
            function_name = f"{runner}-{framework.lower()}"
            if agent_api_url != "https://api.near.ai":
                print(f"Passing agent API URL: {agent_api_url}")
            print(
                f"Running function {function_name} with: assistant_id={run_model.assistant_id}, thread_id={thread_id}, run_id={run_id}"
            )
            invoke_function_via_lambda(function_name, agents, thread_id, run_id, auth, "", params)

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