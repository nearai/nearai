import json
from typing import Any

from openapi_client.api.jobs_api import JobsApi, SelectedJob


def get_pending_job() -> SelectedJob:
    return JobsApi().get_pending_job_v1_jobs_get_pending_job_post()


def update_job(job_id: int, result: Any):
    return JobsApi().update_job_v1_jobs_update_job_post(job_id, json.dumps(result))