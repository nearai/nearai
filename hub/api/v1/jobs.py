import json
from enum import Enum
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import asc, select, update

from hub.api.v1.auth import AuthToken
from hub.api.v1.models import Job, RegistryEntry, get_session
from hub.api.v1.permissions import PermissionVariant, requires_permission
from hub.api.v1.registry import get_read_access

v1_router = APIRouter(
    prefix="/jobs",
    tags=["jobs"],
)


class JobStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"


class WorkerKind(Enum):
    GPU_8_A100 = "GPU_8_A100"
    CPU_MEDIUM = "CPU_MEDIUM"


@v1_router.post("/add_job")
async def add_job(
    worker_kind: WorkerKind,
    entry: RegistryEntry = Depends(get_read_access),
    auth: AuthToken = Depends(requires_permission(PermissionVariant.SUBMIT_JOB)),
) -> Job:
    with get_session() as session:
        job = Job(
            account_id=auth.account_id,
            registry_path=entry.to_location().to_str(),
            worker_kind=worker_kind.value,
            status=JobStatus.PENDING.value,
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        return job


class SelectedJob(BaseModel):
    selected: bool
    job: Optional[Job]
    registry_path: Optional[str]
    info: str


@v1_router.post("/get_pending_job")
def get_pending_job(
    worker_id: str,
    worker_kind: WorkerKind,
    auth: AuthToken = Depends(requires_permission(PermissionVariant.WORKER)),
) -> SelectedJob:
    with get_session() as session:
        for _ in range(5):
            job = session.exec(
                select(Job)
                .where(Job.status == JobStatus.PENDING.value)
                .where(Job.worker_kind == worker_kind.value)
                .order_by(asc(Job.id))
                .limit(1)
            ).first()

            if job is None:
                return SelectedJob(selected=False, job=None, registry_path=None, info="No pending jobs.")

            session.exec(
                update(Job)
                .where(Job.id == job.id)  # type: ignore
                .where(Job.status == JobStatus.PENDING.value)  # type: ignore
                .values(status=JobStatus.PROCESSING.value)
                .values(worker_id=worker_id)
            )
            session.commit()

            # Check if we manage to grab this job
            final_job = session.exec(
                select(Job)
                .where(Job.id == job.id)
                .where(Job.status == JobStatus.PROCESSING.value)
                .where(Job.worker_id == worker_id)
            ).first()

            if final_job is not None:
                return SelectedJob(
                    selected=True,
                    job=final_job,
                    registry_path=final_job.registry_path,
                    info="Job selected.",
                )

    return SelectedJob(selected=False, job=None, registry_path=None, info="Fail to select a job.")


@v1_router.get("/list_jobs")
def list_jobs(
    account_id: Optional[str],
    status: Optional[JobStatus],
    auth: AuthToken = Depends(requires_permission(PermissionVariant.WORKER)),
) -> List[Job]:
    with get_session() as session:
        query = select(Job)

        if account_id is not None:
            query = query.where(Job.account_id == account_id)

        if status is None:
            query = query.where(Job.status != JobStatus.COMPLETED.value)
        else:
            query = query.where(Job.status == status.value)

        return list(session.exec(query).all())


@v1_router.post("/update_job")
async def update_job(
    job_id: int,
    status: JobStatus,
    result_json: str = "",
    auth: AuthToken = Depends(requires_permission(PermissionVariant.WORKER)),
):
    with get_session() as session:
        result = session.exec(select(Job).where(Job.id == job_id)).first()

        if result is None:
            raise HTTPException(status_code=404, detail=f"Job with id `{job_id}` not found.")

        if result.status != JobStatus.PROCESSING.value:
            raise HTTPException(
                status_code=400, detail=f"Job status is not `processing`, instead it is `{result.status}`."
            )
        session.exec(update(Job).where(Job.id == job_id).values(status=status.value, result=json.loads(result_json)))  # type: ignore
        session.commit()
