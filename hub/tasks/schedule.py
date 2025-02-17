import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from functools import partial

from apscheduler.triggers.interval import IntervalTrigger
from fastapi import HTTPException
from nearai.shared.client_config import DEFAULT_MODEL
from nearai.shared.models import RunMode
from sqlmodel import select

from hub.api.v1.auth import AuthToken
from hub.api.v1.models import ScheduledRun, get_session
from hub.api.v1.thread_routes import RunCreateParamsBase, ThreadModel, _create_thread, create_run
from hub.tasks.near_events import near_events_task, process_near_events_initial_state
from hub.tasks.scheduler import get_async_scheduler
from hub.tasks.x_event_source import x_events_task

logger = logging.getLogger(__name__)


async def process_due_tasks(auth_token: AuthToken):
    due_tasks = get_due_tasks()

    if len(due_tasks):
        with get_session() as session:
            for task in due_tasks:
                thread_model = ThreadModel(
                    meta_data={
                        "agent_ids": f"{task.agent}",
                    },
                    tool_resources=None,
                    owner_id=auth_token.account_id,
                )

                if task.thread_id is None:
                    thread = _create_thread(thread_model, auth=auth_token)
                    task.thread_id = thread.id

                model = task.run_params.get("model", DEFAULT_MODEL)

                run_params = RunCreateParamsBase(
                    assistant_id=task.agent,
                    model=model,
                    instructions=None,
                    tools=None,
                    metadata=None,
                    include=[],
                    additional_instructions=None,
                    additional_messages=[{"content": task.input_message, "role": "user"}],
                    max_completion_tokens=None,
                    max_prompt_tokens=None,
                    parallel_tool_calls=None,
                    response_format=None,
                    temperature=None,
                    tool_choice=None,
                    top_p=None,
                    truncation_strategy=None,
                    stream=False,
                    schedule_at=None,
                    delegate_execution=False,
                    parent_run_id=None,
                    run_mode=RunMode.SIMPLE,
                )

                # save successful run attempt in DB
                task.has_run = True
                session.add(task)
                session.commit()

                create_run(thread_id=task.thread_id, run=run_params, auth=auth_token, scheduler=get_async_scheduler())


def get_due_tasks() -> list[ScheduledRun]:
    now = datetime.now()

    with get_session() as session:
        due_tasks = session.exec(
            select(ScheduledRun).where(ScheduledRun.run_at <= now, ScheduledRun.has_run == False)  # noqa: E712
        ).all()

        if due_tasks is None:
            raise HTTPException(status_code=403, detail="ScheduledRun request failed")

        return list(due_tasks)


def load_auth_token():
    """Load the Hub auth token from config."""
    from nearai.config import Config, load_config_file

    app_config = Config()
    # Update config from global config file
    config_data = load_config_file(local=False)
    app_config = app_config.update_with(config_data)

    return app_config.auth


@asynccontextmanager
async def lifespan(app):
    """Schedule recurring tasks."""
    auth_token = load_auth_token()
    read_scheduled_runs = os.getenv("READ_SCHEDULED_RUNS", "false").lower() == "true"
    read_near_events = os.getenv("READ_NEAR_EVENTS", "false").lower() == "true"
    read_x_events = os.getenv("READ_X_EVENTS", "false").lower() == "true"

    if read_scheduled_runs:
        job = partial(process_due_tasks, auth_token)
        get_async_scheduler().add_job(job, IntervalTrigger(seconds=1), name="schedule_run")

    if read_near_events:
        process_near_events_initial_state()
        job = partial(near_events_task, auth_token)
        get_async_scheduler().add_job(job, IntervalTrigger(seconds=1), name="near_events")

    if read_x_events:
        job = partial(x_events_task, auth_token)
        # immediately run the job instead of waiting for the 2 minutes interval
        await job()
        get_async_scheduler().add_job(job, IntervalTrigger(seconds=120), name="x_events")

    if read_near_events or read_x_events or read_scheduled_runs:
        get_async_scheduler().start()

        yield

        get_async_scheduler().shutdown()
    else:
        yield
