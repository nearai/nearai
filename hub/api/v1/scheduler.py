import logging

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler

from hub.api.v1.models import engine

scheduler = BackgroundScheduler()
logging.getLogger("apscheduler").setLevel(logging.DEBUG)


def get_scheduler():
    global scheduler
    if not scheduler.running:
        pg_job_store = SQLAlchemyJobStore(engine=engine)
        scheduler.add_jobstore(jobstore=pg_job_store, alias="sqlalchemy")
        scheduler.start()
    return scheduler
