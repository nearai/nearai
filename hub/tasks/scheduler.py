import logging

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.background import BackgroundScheduler

from hub.api.v1.models import engine

scheduler = BackgroundScheduler()
logging.getLogger("apscheduler").setLevel(logging.WARNING)

async_scheduler = AsyncIOScheduler()


def get_async_scheduler():
    global async_scheduler
    return async_scheduler


def get_scheduler():
    global scheduler
    if not scheduler.running:
        pg_job_store = SQLAlchemyJobStore(engine=engine)

        scheduler.configure(
            jobstores={"default": pg_job_store},
            job_defaults={
                "misfire_grace_time": 60,
            },
        )

        scheduler.start()
    return scheduler
