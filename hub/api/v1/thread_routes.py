import asyncio
import json
import logging
import threading
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from os import getenv
from typing import Any, Dict, Iterable, List, Literal, Optional, Union

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Path, Query
from fastapi.responses import StreamingResponse
from nearai.agents.local_runner import LocalRunner
from nearai.config import load_config_file
from nearai.shared.auth_data import AuthData
from nearai.shared.models import RunMode
from openai import BaseModel
from openai.types.beta.assistant_response_format_option_param import AssistantResponseFormatOptionParam
from openai.types.beta.thread import Thread
from openai.types.beta.thread_create_params import ThreadCreateParams
from openai.types.beta.threads.message import Attachment, Message
from openai.types.beta.threads.message_create_params import MessageContentPartParam
from openai.types.beta.threads.message_update_params import MessageUpdateParams
from openai.types.beta.threads.run import Run as OpenAIRun
from openai.types.beta.threads.run_create_params import AdditionalMessage, TruncationStrategy
from pydantic import Field
from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import asc, desc, select

from hub.api.v1.agent_routes import (
    _runner_for_env,
    get_agent_entry,
    invoke_agent_via_lambda,
    invoke_agent_via_url,
)
from hub.api.v1.auth import AuthToken, get_auth
from hub.api.v1.completions import Provider
from hub.api.v1.models import Delta, get_session
from hub.api.v1.models import Message as MessageModel
from hub.api.v1.models import Run as RunModel
from hub.api.v1.models import Thread as ThreadModel
from hub.api.v1.routes import DEFAULT_TIMEOUT, get_llm_ai
from hub.api.v1.sql import SqlClient
from hub.tasks.scheduler import get_scheduler

STREAMING_RUN_TIMEOUT_MINUTES = 10

threads_router = APIRouter(
    tags=["Threads"],
)

logger = logging.getLogger(__name__)

run_queues: Dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)


class FilterThreadRequestsLogs(logging.Filter):
    """Custom logging filter to suppress spammy healthcheck/status requests.

    Attributes
    ----------
        target_paths: Tuple of path substrings to match for filtering
        target_status: HTTP status code to match for filtering (default: 200)

    """

    def filter(self, record: Any) -> bool:
        """Determine if the specified log record should be logged.

        Args:
        ----
            record: LogRecord object containing all log information

        Returns:
        -------
            bool: False if record matches spam criteria, True otherwise

        Notes:
        -----
            Processes Uvicorn access logs in format:
            `127.0.0.1:PORT - "METHOD PATH HTTP/VERSION" STATUS`

        """
        try:
            log_message = record.getMessage()

            # Early exit for non-request logs
            if '"' not in log_message:
                return True

            # Parse log components
            parts = log_message.split('"')
            request_section = parts[1].strip()  # "GET /path HTTP/1.1"
            status_code = int(parts[-1].split()[-1])  # 200

            # Extract request components
            method, path, _ = request_section.split(" ", 2)

            path_condition = "/v1/threads/thread_" in path

            # Filter condition matching
            return not (path_condition and status_code == 200)

        except Exception as parsing_error:
            print(f"Log parsing failed: {parsing_error}")
            return True


# Configure Uvicorn access logs filtering
if getenv("HIDE_THREADS_REQUEST_LOGS", False):
    # Uvicorn access logger instance with custom filtering applied
    logging.getLogger("uvicorn.access").addFilter(FilterThreadRequestsLogs())


SUMMARY_PROMPT = """You are an expert at summarizing conversations in a maximum of 5 words.

**Instructions:**

- Provide a concise summary of the conversation in 5 words or less.
- Focus on the main topic or action discussed.
- **Do not** include any additional text, explanations, or greetings.

**Example Responses:**

- Weather in Tokyo
- Trip to Lisbon
- Career change advice
- Book recommendation request
- Tech support for laptop
"""


@threads_router.post("/threads")
def create_thread(
    thread: ThreadCreateParams = Body(...),
    auth: AuthToken = Depends(get_auth),
) -> Thread:
    thread_model = ThreadModel(
        messages=thread["messages"] if "messages" in thread else [],
        meta_data=thread["metadata"] if "metadata" in thread else None,
        tool_resources=thread["tool_resources"] if "tool_resources" in thread else None,
        owner_id=auth.account_id,
    )

    return _create_thread(thread_model, auth)


def _create_thread(thread_model: ThreadModel, auth: AuthToken = Depends(get_auth)) -> Thread:
    with get_session() as session:
        thread_model.owner_id = auth.account_id
        session.add(thread_model)
        session.commit()
        return thread_model.to_openai()


@threads_router.get("/threads")
def list_threads(
    include_subthreads: Optional[bool] = Query(
        True, description="Include threads that have a parent_id - defaults to true"
    ),
    auth: AuthToken = Depends(get_auth),
) -> List[Thread]:
    with get_session() as session:
        statement = select(ThreadModel).where(ThreadModel.owner_id == auth.account_id)

        if include_subthreads is not True:
            statement = statement.where(ThreadModel.parent_id == None)  # noqa: E711

        threads = session.exec(statement).all()
        return [thread.to_openai() for thread in threads]


@threads_router.get("/threads/{thread_id}")
def get_thread(
    thread_id: str,
    auth: AuthToken = Depends(get_auth),
) -> Thread:
    with get_session() as session:
        thread_model = _check_thread_permissions(auth, session, thread_id)
        return thread_model.to_openai()


class ThreadUpdateParams(BaseModel):
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Set of 16 key-value pairs that can be attached to an object."
    )
    tool_resources: Optional[Dict[str, Any]] = Field(
        None, description="A set of resources that are made available to the assistant's tools in this thread."
    )


@threads_router.post("/threads/{thread_id}")
def update_thread(
    thread_id: str,
    thread: ThreadUpdateParams = Body(...),
    auth: AuthToken = Depends(get_auth),
) -> Thread:
    with get_session() as session:
        thread_model = _check_thread_permissions(auth, session, thread_id)

        if thread.metadata is not None:
            thread_model.meta_data = thread.metadata

        if thread.tool_resources is not None:
            thread_model.tool_resources = thread.tool_resources

        session.add(thread_model)
        session.commit()
        return thread_model.to_openai()


class ThreadDeletionStatus(BaseModel):
    id: str
    object: str = "thread.deleted"
    deleted: bool = True


@threads_router.delete("/threads/{thread_id}")
def delete_thread(
    thread_id: str,
    auth: AuthToken = Depends(get_auth),
) -> ThreadDeletionStatus:
    with get_session() as session:
        thread_model = _check_thread_permissions(auth, session, thread_id)

        session.delete(thread_model)
        session.commit()

        return ThreadDeletionStatus(id=thread_id)


class MessageCreateParams(BaseModel):
    content: Union[str, Iterable[MessageContentPartParam]]
    """The text contents of the message."""

    role: Literal["user", "assistant", "system"]
    """The role of the entity that is creating the message. Allowed values include:

    - `user`: Indicates the message is sent by an actual user and should be used in
      most cases to represent user-generated messages.
    - `assistant`: Indicates the message is generated by the assistant. Use this
      value to insert messages from the assistant into the conversation.
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

    run_id: Optional[str] = None
    """The ID of the run creating the message."""


class ThreadForkResponse(BaseModel):
    id: str
    object: str = "thread"
    created_at: int
    metadata: Optional[dict] = None


@threads_router.post("/threads/{thread_id}/fork")
def fork_thread(
    thread_id: str,
    auth: AuthToken = Depends(get_auth),
) -> ThreadForkResponse:
    with get_session() as session:
        original_thread = _check_thread_permissions(auth, session, thread_id)

        # Create a new thread as a copy of the original
        forked_thread = ThreadModel(
            messages=[],  # Start with an empty message list
            meta_data=original_thread.meta_data,
            tool_resources=original_thread.tool_resources,
            owner_id=auth.account_id,
        )
        session.add(forked_thread)
        session.flush()  # Flush to generate the new thread's ID

        # Copy messages from the original thread to the forked thread
        messages = session.exec(
            select(MessageModel).where(MessageModel.thread_id == thread_id).order_by(asc(MessageModel.created_at))
        ).all()

        for message in messages:
            forked_message = MessageModel(
                thread_id=forked_thread.id,
                content=message.content,
                role=message.role,
                assistant_id=message.assistant_id,
                meta_data=message.meta_data,
                attachments=message.attachments,
                run_id=message.run_id,
            )
            session.add(forked_message)

        session.commit()

        return ThreadForkResponse(
            id=forked_thread.id,
            created_at=int(forked_thread.created_at.timestamp()),
            metadata=forked_thread.meta_data,
        )


class SubthreadCreateParams(BaseModel):
    messages_to_copy: Optional[List[int]] = []
    new_messages: Optional[List[MessageCreateParams]] = []


@threads_router.post("/threads/{parent_id}/subthread")
def create_subthread(
    parent_id: str,
    subthread_params: SubthreadCreateParams = Body(...),
    auth: AuthToken = Depends(get_auth),
) -> Thread:
    with get_session() as session:
        parent_thread = session.get(ThreadModel, parent_id)
        if parent_thread is None:
            raise HTTPException(status_code=404, detail="Parent thread not found")

        if parent_thread.owner_id != auth.account_id:
            raise HTTPException(
                status_code=403, detail="You don't have permission to create a subthread for this thread"
            )

        subthread = ThreadModel(
            messages=[],
            meta_data=parent_thread.meta_data,
            tool_resources=parent_thread.tool_resources,
            owner_id=auth.account_id,
            parent_id=parent_id,
        )
        session.add(subthread)
        session.flush()  # Flush to generate the new thread's ID

        # Copy specified messages from the parent thread
        if subthread_params.messages_to_copy:
            messages = session.exec(
                select(MessageModel)
                .where(MessageModel.id.in_(subthread_params.messages_to_copy))  # type: ignore
                .where(MessageModel.thread_id == parent_id)
            ).all()
            for message in messages:
                new_message = MessageModel(
                    thread_id=subthread.id,
                    content=message.content,
                    role=message.role,
                    assistant_id=message.assistant_id,
                    meta_data=message.meta_data,
                    attachments=message.attachments,
                    run_id=message.run_id,
                )
                session.add(new_message)

        # Add new messages to the subthread
        if subthread_params.new_messages:
            for new_message_params in subthread_params.new_messages:
                new_message = MessageModel(
                    thread_id=subthread.id,
                    content=new_message_params.content,
                    role=new_message_params.role,
                    assistant_id=new_message_params.assistant_id,
                    meta_data=new_message_params.metadata,
                    attachments=new_message_params.attachments,
                    run_id=new_message_params.run_id,
                )
                session.add(new_message)

        session.commit()
        return subthread.to_openai()


@threads_router.post("/threads/{thread_id}/messages")
def create_message(
    thread_id: str,
    background_tasks: BackgroundTasks,
    message: MessageCreateParams = Body(...),
    auth: AuthToken = Depends(get_auth),
) -> Message:
    with get_session() as session:
        thread = _check_thread_permissions(auth, session, thread_id)

        if not message.content:
            message.content = " "  # OpenAI format requires content to be non-empty

        message_model = MessageModel(
            thread_id=thread_id,
            content=message.content,
            role=message.role,
            assistant_id=message.assistant_id,
            meta_data=message.metadata,
            attachments=message.attachments,
            run_id=message.run_id,
        )
        logger.info(f"Created message: {message_model}")
        session.add(message_model)
        session.commit()

        if not thread.meta_data or not thread.meta_data.get("topic"):
            background_tasks.add_task(generate_thread_topic, thread_id)

        return message_model.to_openai()


def generate_thread_topic(thread_id: str):
    # not much error handling in here – it's OK if this fails
    with get_session() as session:
        thread = session.get(ThreadModel, thread_id)
        if thread is None:
            raise HTTPException(status_code=404, detail="Thread not found")

        messages = session.exec(
            select(MessageModel)
            .where(MessageModel.thread_id == thread_id)
            .where(MessageModel.role != "assistant")
            .order_by(desc(MessageModel.created_at))
            .limit(1)
        ).all()

        messages = [
            {
                "role": "system",
                "content": SUMMARY_PROMPT,
            }
        ] + [message.to_completions_model() for message in messages]

        llm = get_llm_ai(Provider.FIREWORKS.value)
        resp = llm.chat.completions.create(
            messages=messages, model="accounts/fireworks/models/qwen2p5-72b-instruct", timeout=DEFAULT_TIMEOUT
        )

    with get_session() as session:
        thread = session.get(ThreadModel, thread_id)

        if thread is None:
            raise HTTPException(status_code=404, detail="Thread not found")

        if thread.meta_data is None:
            thread.meta_data = {}

        thread.meta_data["topic"] = resp.choices[0].message.content
        flag_modified(thread, "meta_data")  # SQLAlchemy is not detecting changes in the dict, forcing a commit.
        session.commit()


class ListMessagesResponse(BaseModel):
    object: Literal["list"]
    data: List[Message]
    has_more: bool
    first_id: str
    last_id: str


@threads_router.get("/threads/{thread_id}/messages")
def list_messages(
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
    auth: AuthToken = Depends(get_auth),
    include_subthreads: bool = True,
) -> ListMessagesResponse:
    logger.debug(f"Listing messages for thread: {thread_id}")
    with get_session() as session:
        _check_thread_permissions(auth, session, thread_id)

        child_threads = (
            session.exec(select(ThreadModel.id).where(ThreadModel.parent_id == thread_id)).all()
            if include_subthreads
            else []
        )

        statement = select(MessageModel).where(
            MessageModel.thread_id.in_([thread_id] + list(child_threads))  # type: ignore
        )

        # Apply filters
        if after:
            after_message = session.get(MessageModel, after)
            if after_message:
                statement = statement.where(MessageModel.created_at > after_message.created_at)

        if run_id:
            statement = statement.where(MessageModel.run_id == run_id)

        # Apply order
        if order == "asc":
            statement = statement.order_by(asc(MessageModel.created_at))
        else:
            statement = statement.order_by(desc(MessageModel.created_at))

        if before:
            before_message = session.get(MessageModel, before)
            if before_message:
                if order == "asc":
                    statement = statement.where(MessageModel.created_at < before_message.created_at)
                else:
                    statement = statement.where(MessageModel.created_at > before_message.created_at)

        # Apply limit
        statement = statement.limit(limit)

        # Print the SQL query
        logger.debug("SQL Query:", statement.compile(compile_kwargs={"literal_binds": True}))

        messages = session.exec(statement).all()
        logger.debug(
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
def modify_message(
    message_id: str,
    message: MessageUpdateParams = Body(...),
    auth: AuthToken = Depends(get_auth),
) -> Message:
    with get_session() as session:
        message_model = session.get(MessageModel, message_id)
        if message_model is None:
            raise HTTPException(status_code=404, detail="Message not found")

        thread_id = message_model.thread_id
        _check_thread_permissions(auth, session, thread_id)

        message_model.meta_data = message["metadata"] if isinstance(message["metadata"], dict) else None
        session.commit()
        return message_model.to_openai()


class RunCreateParamsBase(BaseModel):
    assistant_id: str = Field(..., description="The ID of the assistant to use to execute this run.")
    # Overrides model in agent metadata.
    model: str = Field(default="", description="The ID of the Model to be used to execute this run.")
    instructions: Optional[str] = Field(
        None,
        description=(
            "Overrides the instructions of the assistant. This is useful for modifying the behavior on a per-run basis."
        ),
    )
    tools: Optional[List[dict]] = Field(None, description="Override the tools the assistant can use for this run.")
    metadata: Optional[dict] = Field(None, description="Set of 16 key-value pairs that can be attached to an object.")

    include: List[dict] = Field([], description="A list of additional fields to include in the response.")
    additional_instructions: Optional[str] = Field(
        None, description="Appends additional instructions at the end of the instructions for the run."
    )
    additional_messages: Optional[List[AdditionalMessage]] = Field(
        None, description="Adds additional messages to the thread before creating the run."
    )
    # Ignored
    max_completion_tokens: Optional[int] = Field(
        None, description="The maximum number of completion tokens that may be used over the course of the run."
    )
    # Ignored
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
    # Ignored
    tool_choice: Optional[Union[str, dict]] = Field(
        None, description="Controls which (if any) tool is called by the model."
    )
    # Ignored
    top_p: Optional[float] = Field(
        None, description="An alternative to sampling with temperature, called nucleus sampling."
    )
    truncation_strategy: Optional[TruncationStrategy] = Field(
        None, description="Controls for how a thread will be truncated prior to the run."
    )
    stream: bool = Field(False, description="Whether to stream the run.")

    # Custom fields
    schedule_at: Optional[datetime] = Field(None, description="The time at which the run should be scheduled.")
    delegate_execution: bool = Field(False, description="Whether to delegate execution to an external actor.")
    parent_run_id: Optional[str] = Field(None, description="The ID of the run that this run is triggered by.")
    run_mode: Optional[RunMode] = Field(RunMode.SIMPLE, description="The mode in which the run should be executed.")


@threads_router.post("/threads/{thread_id}/runs")
def create_run(
    thread_id: str,
    run: RunCreateParamsBase = Body(...),
    auth: AuthToken = Depends(get_auth),
    scheduler=Depends(get_scheduler),
):
    logger.info(f"Creating run for thread: {thread_id}")
    with get_session() as session:
        thread_model = _check_thread_permissions(auth, session, thread_id)

        if not thread_model.meta_data:
            thread_model.meta_data = {}
        if not thread_model.meta_data.get("agent_ids"):
            thread_model.meta_data["agent_ids"] = []
        if run.assistant_id not in thread_model.meta_data["agent_ids"]:
            thread_model.meta_data["agent_ids"].append(run.assistant_id)
            flag_modified(
                thread_model, "meta_data"
            )  # SQLAlchemy is not detecting changes in the dict, forcing a commit.
            session.commit()

        if run.additional_messages:
            messages = []
            for message in run.additional_messages:
                messages.append(
                    MessageModel(
                        thread_id=thread_id,
                        content=message["content"],
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
            instructions=(run.instructions or "") + (run.additional_instructions or ""),
            tools=run.tools,
            metadata=run.metadata,
            max_completion_tokens=run.max_completion_tokens,
            max_prompt_tokens=run.max_prompt_tokens,
            parallel_tool_calls=run.parallel_tool_calls,
            response_format=run.response_format,
            temperature=run.temperature,
            tool_choice=run.tool_choice,
            top_p=run.top_p,
            truncation_strategy=run.truncation_strategy,
            status="queued",
            parent_run_id=run.parent_run_id,
            child_run_ids=[],
            run_mode=run.run_mode,
        )

        session.add(run_model)
        session.commit()

        if run.stream:
            run_queues[run_model.id] = asyncio.Queue()

            # 1. Event: thread.run.created
            event_created = _streaming_run_event("thread.run.created", run_model, thread_id)
            asyncio.run(run_queues[run_model.id].put(event_created))

            # 2. Event: thread.run.queued
            event_queued = _streaming_run_event("thread.run.queued", run_model, thread_id)
            asyncio.run(run_queues[run_model.id].put(event_queued))

            # 3. Event: thread.run.in_progress
            event_in_progress = _streaming_run_event("thread.run.in_progress", run_model, thread_id)
            # Update the payload for in_progress status
            event_in_progress["data"]["status"] = "in_progress"
            event_in_progress["data"]["started_at"] = int(datetime.now(timezone.utc).timestamp())
            asyncio.run(run_queues[run_model.id].put(event_in_progress))

            # 4. Event: thread.run.step.created
            event_step_created, step_payload = _streaming_step_event("thread.run.step.created", run_model, thread_id)
            asyncio.run(run_queues[run_model.id].put(event_step_created))

            # 5. Event: thread.run.step.in_progress
            event_step_in_progress = _streaming_step_event("thread.run.step.in_progress", run_model, thread_id)
            asyncio.run(run_queues[run_model.id].put(event_step_in_progress))

            if not run.delegate_execution:
                thread = threading.Thread(target=_run_agent, args=(thread_id, run_model.id, None, auth))
                thread.start()

            return StreamingResponse(stream_run_events(run_model.id, True), media_type="text/event-stream")

        if run.delegate_execution:
            return run_model.to_openai()

        # Queue the run
        scheduler.add_job(
            _run_agent,
            "date",
            run_date=run.schedule_at or datetime.now(),
            args=[thread_id, run_model.id, None, auth],
            jobstore="default",
        )

        return run_model.to_openai()


def run_agent(
    thread_id: str,
    run_id: str,
    background_tasks: BackgroundTasks,
    auth: AuthToken = Depends(get_auth),
) -> OpenAIRun:
    """Task to run an agent in the background."""
    return _run_agent(thread_id, run_id, background_tasks, auth)


def _run_agent(
    thread_id: str,
    run_id: str,
    background_tasks: Optional[BackgroundTasks] = None,
    auth: AuthToken = Depends(get_auth),
) -> OpenAIRun:
    with get_session() as session:
        run_model = session.get(RunModel, run_id)
        if run_model is None:
            raise HTTPException(status_code=404, detail="Run not found")
        agent_api_url = getenv("API_URL", "https://api.near.ai")
        data_source = getenv("DATA_SOURCE", "registry")

        agent_env_vars: Dict[str, Any] = {}
        user_env_vars: Dict[str, Any] = {}

        agent_entry = get_agent_entry(run_model.assistant_id, data_source)

        if not agent_entry:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_entry}' not found in the registry.")

        specific_agent_version_to_run = (
            f"{agent_entry.namespace}/{agent_entry.name}/{agent_entry.version}"
            if agent_entry
            else run_model.assistant_id
        )

        logger.info(
            f"Running agent {specific_agent_version_to_run} "
            f"for run: {run_id} on thread: {thread_id}. Signed by {auth.account_id}."
        )

        # TODO#733 Optimization with using agent.identifier
        specific_agent_version_entry = get_agent_entry(specific_agent_version_to_run, data_source)
        # read secret for every requested agent
        if specific_agent_version_entry:
            agent_env_vars[specific_agent_version_to_run] = specific_agent_version_entry.details.get("env_vars", {})
            db = SqlClient()

            (agent_secrets, user_secrets) = db.get_agent_secrets(
                auth.account_id,
                specific_agent_version_entry.namespace,
                specific_agent_version_entry.name,
                specific_agent_version_entry.version,
            )

            # agent vars from metadata has lower priority then agent secret
            agent_env_vars[specific_agent_version_to_run] = {
                **(agent_env_vars.get(specific_agent_version_to_run, {})),
                **agent_secrets,
            }

            # user vars from url has higher priority then user secret
            user_env_vars = {**user_secrets, **user_env_vars}

        params = {
            "record_run": True,
            "api_url": agent_api_url,
            "tool_resources": run_model.tools,
            "data_source": data_source,
            "model": run_model.model,
            "temperature": run_model.temperature,
            "user_env_vars": user_env_vars,
            "agent_env_vars": agent_env_vars,
        }
        runner = _runner_for_env()

        framework = agent_entry.get_framework()

        run_model.status = "in_progress"
        run_model.started_at = datetime.now()
        session.commit()

        if runner == "custom_runner":
            custom_runner_url = getenv("CUSTOM_RUNNER_URL", None)
            if custom_runner_url:
                invoke_agent_via_url(custom_runner_url, specific_agent_version_to_run, thread_id, run_id, auth, params)
            else:
                raise HTTPException(status_code=400, detail="Runner invoke URL not set for local runner")
        elif runner == "local_runner":
            """Runs agents directly from the local machine."""

            params["api_url"] = load_config_file()["api_url"]

            LocalRunner(
                None,
                run_model.assistant_id,
                thread_id,
                run_id,
                AuthData(**auth.model_dump()),  # TODO: https://github.com/nearai/nearai/issues/421
                params,
            )
        else:
            function_name = f"{runner}-{framework.lower()}"
            if agent_api_url != "https://api.near.ai":
                print(f"Passing agent API URL: {agent_api_url}")
            print(
                f"Running function {function_name} with: "
                f"assistant_id={run_model.assistant_id}, "
                f"thread_id={thread_id}, run_id={run_id}, "
                f"user_secrets:{len(user_secrets)}, agent_secrets:{len(agent_secrets)}"
            )
            invoke_agent_via_lambda(function_name, specific_agent_version_to_run, thread_id, run_id, auth, params)
        # with get_session() as session:
        if run_model.parent_run_id:
            parent_run = session.get(RunModel, run_model.parent_run_id)
            if parent_run:
                # check parent_run_id of the parent for loops
                if parent_run.parent_run_id:
                    raise HTTPException(
                        status_code=400,
                        detail="Parent run cannot have a parent run. Parent run is already a child run of another run.",
                    )

                parent_run.child_run_ids.append(run_id)
                flag_modified(parent_run, "child_run_ids")  # SQLAlchemy is not detecting changes...
                session.commit()
                logger.info(f"Calling parent run: {parent_run.id}, after child run: {run_id}")

                if run_model.run_mode == RunMode.WITH_CALLBACK:
                    if background_tasks:
                        background_tasks.add_task(run_agent, thread_id, parent_run.id, background_tasks, auth)
                    else:
                        _run_agent(thread_id, parent_run.id, auth=auth)
        return run_model.to_openai()


async def monitor_deltas(run_id: str, delete: bool):
    with get_session() as session:
        start_time = datetime.now(timezone.utc)
        last_seen_id = 0  # Track by ID instead of storing all IDs in memory

        async def handle_delete():
            if delete:
                await asyncio.sleep(3)  # Let the other listeners get this event
                session.query(Delta).filter(Delta.run_id == run_id).delete()
                session.commit()

        completion = None
        while True:
            try:
                # Fetch events with ID greater than last_seen_id
                query = (
                    select(Delta)
                    .where(Delta.run_id == run_id, Delta.id > last_seen_id)
                    .order_by(asc(Delta.id))
                    .limit(10)  # Process in small batches
                )
                events = session.exec(query).all()

                # Set a maximum run time
                if datetime.now(timezone.utc) - start_time >= timedelta(minutes=STREAMING_RUN_TIMEOUT_MINUTES):
                    logger.error(f"Timeout reached for monitor_deltas on run_id {run_id}")
                    run_model = session.get(RunModel, run_id)
                    event = _streaming_run_event(
                        "thread.run.expired", run_model, run_model.thread_id if run_model else ""
                    )
                    await run_queues[run_id].put(event)
                    await handle_delete()
                    return

                if not events:
                    if completion:
                        # send completion event last
                        await run_queues[run_id].put(completion)
                        await handle_delete()
                        return
                    await asyncio.sleep(0.1)  # Longer sleep when no events
                    continue

                for event in events:
                    last_seen_id = max(last_seen_id, event.id)
                    payload = {"id": event.message_id, "object": event.object, "delta": event.content}
                    event_data = {
                        "event": event.object,
                        "data": payload,
                    }

                    if hasattr(event, "object") and event.object == "thread.run.completed":
                        # Signal completion but continue processing events
                        completion = event_data
                    else:
                        # Send event
                        await run_queues[run_id].put(event_data)

                await asyncio.sleep(0.05)  # Poll more frequently
            except Exception as e:
                logger.error(f"Error in monitor_deltas for run_id {run_id}: {e}")
                await asyncio.sleep(1)  # Wait before retrying


async def stream_run_events(run_id: str, delete: bool):
    asyncio.create_task(monitor_deltas(run_id, delete))
    logger.info(f"Started monitor_deltas task for run_id {run_id}")
    queue = run_queues[run_id]
    while True:
        event = await queue.get()
        yield f"data: {json.dumps(event)}\n\n"
        await asyncio.sleep(0)
        if (
            event
            and hasattr(event, "event")
            and event.event
            in ["thread.run.completed", "thread.run.failed", "thread.run.cancelled", "thread.run.expired"]
        ):
            break
    del run_queues[run_id]


@threads_router.get("/threads/{thread_id}/stream/{run_id}")
async def thread_subscribe(thread_id: str, run_id: Optional[str] = None, auth: AuthToken = Depends(get_auth)):
    """Subscribe to deltas for a thread and run (for client channels outside of the run)."""
    with get_session() as session:
        if run_id:
            run = session.get(RunModel, run_id)
        else:
            run = session.exec(
                select(RunModel).where(RunModel.thread_id == thread_id).order_by(desc(RunModel.created_at))
            ).first()
        if not run:
            raise HTTPException(status_code=404, detail="Run for thread not found")
        _check_thread_permissions(auth, session, thread_id)

        return StreamingResponse(
            stream_run_events(run.id, False),
            media_type="text/event-stream",
            headers={"X-Accel-Buffering": "no", "Content-Type": "text/event-stream", "Cache-Control": "no-cache"},
        )


@threads_router.get("/threads/{thread_id}/runs/{run_id}")
def get_run(
    thread_id: str = Path(..., description="The ID of the thread"),
    run_id: str = Path(..., description="The ID of the run"),
    auth: AuthToken = Depends(get_auth),
) -> OpenAIRun:
    """Get details of a specific run for a thread."""
    with get_session() as session:
        _check_thread_permissions(auth, session, thread_id)
        run_model = session.get(RunModel, run_id)
        if run_model is None:
            raise HTTPException(status_code=404, detail="Run not found")

        if run_model.thread_id != thread_id:
            raise HTTPException(status_code=404, detail="Run not found for this thread")

        return run_model.to_openai()


class RunUpdateParams(BaseModel):
    status: Optional[Literal["requires_action", "failed", "expired", "completed"]] = None
    completed_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    metadata: Optional[dict] = None


@threads_router.post("/threads/{thread_id}/runs/{run_id}")
def update_run(
    thread_id: str,
    run_id: str,
    run: RunUpdateParams = Body(...),
    auth: AuthToken = Depends(get_auth),
) -> OpenAIRun:
    with get_session() as session:
        _check_thread_permissions(auth, session, thread_id)
        run_model = session.get(RunModel, run_id)
        if run_model is None:
            raise HTTPException(status_code=404, detail="Run not found")

        if run.status:
            run_model.status = run.status
        if run.completed_at:
            run_model.completed_at = run.completed_at
        if run.metadata:
            run_model.meta_data = run.metadata
        if run.failed_at:
            run_model.failed_at = run.failed_at

        session.add(run_model)
        session.commit()
        if run_queues.get(run_id):
            # add to deltas instead of run queue so it doesn't skip ahead of in flight deltas
            delta = Delta(
                run_id=run_id,
                object=f"thread.run.{run.status}",
                content=_streaming_run_event(f"thread.run.{run.status}", run_model, thread_id)["data"],
            )
            session.add(delta)
            session.commit()

        return run_model.to_openai()


def _check_thread_permissions(auth, session, thread_id) -> ThreadModel:
    thread = session.get(ThreadModel, thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    if thread.owner_id != auth.account_id:
        raise HTTPException(status_code=403, detail="You don't have permission to access messages from this thread")
    return thread


def _streaming_run_event(event_name, run_model, thread_id):
    base_payload = {
        "id": run_model.id,  # e.g., "run_123"
        "object": "thread.run",
        "created_at": int(datetime.now(timezone.utc).timestamp()),
        "assistant_id": run_model.assistant_id,
        "thread_id": thread_id,
        "status": "queued",
        "started_at": None,
        "expires_at": int((datetime.now(timezone.utc) + timedelta(minutes=STREAMING_RUN_TIMEOUT_MINUTES)).timestamp()),
        "cancelled_at": None,
        "failed_at": None,
        "completed_at": None,
        "required_action": None,
        "last_error": None,
        "model": run_model.model,
        "instructions": run_model.instructions,
        "tools": run_model.tools,
        "metadata": run_model.meta_data if isinstance(run_model.metadata, dict) else None,
        "temperature": run_model.temperature,
        "top_p": run_model.top_p,
        "max_completion_tokens": run_model.max_completion_tokens,
        "max_prompt_tokens": run_model.max_prompt_tokens,
        "truncation_strategy": run_model.truncation_strategy,
        "incomplete_details": None,
        "usage": None,
        "response_format": run_model.response_format,
        "tool_choice": run_model.tool_choice,
        "parallel_tool_calls": run_model.parallel_tool_calls,
    }
    event = {
        "event": event_name,
        "data": base_payload,
    }
    return event


def _streaming_step_event(event_name, run_model, thread_id):
    expires_at = int((datetime.now(timezone.utc) + timedelta(minutes=STREAMING_RUN_TIMEOUT_MINUTES)).timestamp())
    step_payload = {
        "id": "step_001",  # placeholder step id
        "object": "thread.run.step",
        "created_at": int(datetime.now(timezone.utc).timestamp()),
        "run_id": run_model.id,
        "assistant_id": run_model.assistant_id,
        "thread_id": thread_id,
        "type": "message_creation",
        "status": "in_progress",
        "cancelled_at": None,
        "completed_at": None,
        "expires_at": expires_at,
        "failed_at": None,
        "last_error": None,
        "step_details": {
            "type": "message_creation",
            "message_creation": {
                "message_id": "msg_001",  # placeholder message id
            },
        },
        "usage": None,
    }
    event_step_created = {
        "event": event_name,
        "data": step_payload,
    }
    return event_step_created, step_payload
