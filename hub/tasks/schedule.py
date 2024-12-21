import os
from contextlib import asynccontextmanager
from functools import partial

from apscheduler.triggers.interval import IntervalTrigger

from hub.tasks.near_events import near_events_task, process_near_events_initial_state
from hub.tasks.scheduler import get_async_scheduler
from hub.tasks.x_event_source import process_x_events_initial_state, x_events_task


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
    read_near_events = os.getenv("READ_NEAR_EVENTS", "false").lower() == "true"
    read_x_events = os.getenv("READ_X_EVENTS", "false").lower() == "true"

    if read_near_events:
        process_near_events_initial_state()
        job = partial(near_events_task, auth_token)

        get_async_scheduler().add_job(job, IntervalTrigger(seconds=1))

    if read_x_events:
        process_x_events_initial_state()
        job = partial(x_events_task, auth_token)
        get_async_scheduler().add_job(job, IntervalTrigger(seconds=120))

    if read_near_events or read_x_events:
        get_async_scheduler().start()

        yield

        get_async_scheduler().shutdown()
    else:
        yield
