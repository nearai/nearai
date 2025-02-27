import asyncio
import logging
import os
import signal
import sys
from datetime import datetime
from functools import partial

from apscheduler.triggers.interval import IntervalTrigger
from ddtrace import patch_all
from dotenv import load_dotenv
from nearai.shared.models import RunMode
from sqlmodel import select

# Import necessary modules from the hub package
from hub.api.v1.auth import AuthToken
from hub.api.v1.models import ScheduledRun, get_session
from hub.api.v1.thread_routes import RunCreateParamsBase, ThreadModel, _create_thread, create_run
from hub.tasks.near_events import near_events_task, process_near_events_initial_state
from hub.tasks.scheduler import get_async_scheduler
from hub.tasks.x_event_source import x_events_task

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

if os.environ.get("DD_ENABLED"):
    patch_all()


class WarningFilter(logging.Filter):
    """Filter to suppress APScheduler warning messages."""

    def filter(self, record):
        """Filter out APScheduler warning messages which are not relevant."""
        msg = record.getMessage()
        # It is expected that the maximum number of running instances may be reached because of the scheduler design
        # We're always trying to download the block that does not exist yet
        if "skipped: maximum number of running instances reached" in msg:
            return False
        return True


logger = logging.getLogger("apscheduler.scheduler")
logger.addFilter(WarningFilter())


load_dotenv()


def load_auth_token():
    """Load the Hub auth token from config."""
    from nearai.config import Config, load_config_file

    app_config = Config()
    # Update config from global config file
    config_data = load_config_file(local=False)
    app_config = app_config.update_with(config_data)

    return app_config.auth


async def process_due_tasks(auth_token: AuthToken):
    """Process tasks that are due to run."""
    due_tasks = get_due_tasks()

    if len(due_tasks):
        with get_session() as session:
            for task in due_tasks:
                logger.info(f"Processing scheduled_run for {task.agent}, task_id: {task.id}")

                try:
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

                    model = task.run_params.get("model", "")

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

                    create_run(
                        thread_id=task.thread_id, run=run_params, auth=auth_token, scheduler=get_async_scheduler()
                    )
                    logger.info(f"Successfully processed task for agent {task.agent}")
                except Exception as e:
                    logger.error(f"Error processing task: {e}")


def get_due_tasks() -> list[ScheduledRun]:
    """Get tasks that are due to run."""
    try:
        now = datetime.now()

        with get_session() as session:
            due_tasks = session.exec(
                select(ScheduledRun).where(ScheduledRun.run_at <= now, ScheduledRun.has_run == False)  # noqa: E712
            ).all()

            return list(due_tasks) if due_tasks else []
    except Exception as e:
        logger.error(f"Error getting due tasks: {e}")
        return []


async def main():
    """Main function to set up and run the scheduler."""
    logger.info("Starting scheduler process")

    # Set up signal handlers for graceful shutdown
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(shutdown(s)))

    # Load auth token
    auth_token = load_auth_token()

    # Get configuration from environment variables
    read_scheduled_runs = os.getenv("READ_SCHEDULED_RUNS", "false").lower() == "true"
    read_near_events = os.getenv("READ_NEAR_EVENTS", "false").lower() == "true"
    read_x_events = os.getenv("READ_X_EVENTS", "false").lower() == "true"

    logger.info(
        f"Events configuration: Scheduled runs: {read_scheduled_runs}, NEAR: {read_near_events}, X: {read_x_events}"
    )

    scheduler = get_async_scheduler()

    # Set up scheduled jobs
    if read_scheduled_runs:
        job = partial(process_due_tasks, auth_token)
        scheduler.add_job(job, IntervalTrigger(seconds=1), name="schedule_run")
        logger.info("Added scheduled runs job")

    if read_near_events:
        process_near_events_initial_state()
        job = partial(near_events_task, auth_token)
        scheduler.add_job(
            job,
            IntervalTrigger(seconds=1),
            name="near_events",
            max_instances=1,  # ABSOLUTELY CRUCIAL - only 1 concurrent job
            coalesce=True,  # Combine missed executions into one
            misfire_grace_time=10,  # Allow some delay for busy system
            replace_existing=True,  # Ensure no duplicate jobs
        )
        logger.info("Added near events job")

    if read_x_events:
        job = partial(x_events_task, auth_token)
        # immediately run the job
        await job()
        scheduler.add_job(job, IntervalTrigger(seconds=120), name="x_events")
        logger.info("Added X events job")

    if read_near_events or read_x_events or read_scheduled_runs:
        scheduler.start()
        logger.info("Scheduler started")

        # Keep the event loop running
        while True:
            await asyncio.sleep(1)
    else:
        logger.warning("No jobs configured. Scheduler will exit.")


async def shutdown(signal):
    """Handle graceful shutdown."""
    logger.info(f"Received exit signal {signal.name}...")
    scheduler = get_async_scheduler()

    if scheduler.running:
        logger.info("Shutting down scheduler...")
        scheduler.shutdown()

    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]

    if tasks:
        logger.info(f"Cancelling {len(tasks)} outstanding tasks")
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    logger.info("Shutdown complete")
    asyncio.get_event_loop().stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by keyboard interrupt")
    except Exception as e:
        logger.error(f"Scheduler stopped due to error: {e}")
        sys.exit(1)
