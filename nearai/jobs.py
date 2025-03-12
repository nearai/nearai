import json
from typing import Any, List, Optional

from nearai.openapi_client.api.jobs_api import Job, JobsApi, JobStatus, SelectedJob, WorkerKind


def get_pending_job(worker_id: str, worker_kind: WorkerKind) -> SelectedJob:
    return JobsApi().get_pending_job_v1_jobs_get_pending_job_post(worker_id, worker_kind)


def list_jobs(account_id: Optional[str], status: Optional[JobStatus]) -> List[Job]:
    return JobsApi().list_jobs_v1_jobs_list_jobs_get(account_id=account_id, status=status)


def update_job(job_id: int, status: JobStatus, result: Any):
    return JobsApi().update_job_v1_jobs_update_job_post(job_id, status, json.dumps(result))
