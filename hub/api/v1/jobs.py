import json
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlmodel import asc, select, update

from hub.api.v1.auth import AuthToken
from hub.api.v1.models import Jobs, get_session
from hub.api.v1.permissions import PermissionVariant, requires_permission
from hub.api.v1.registry import S3_BUCKET, s3

v1_router = APIRouter(
    prefix="/jobs",
    tags=["jobs"],
)


@v1_router.post("/add_job")
async def add_job(
    auth: AuthToken = Depends(requires_permission(PermissionVariant.SUBMIT_JOB)), file: UploadFile = File(...)
):
    with get_session() as session:
        key = f"jobs/{auth.account_id}/{uuid.uuid4().hex[:16]}"
        assert S3_BUCKET is not None
        s3.upload_fileobj(file.file, S3_BUCKET, key)
        session.add(Jobs(account_id=auth.account_id, registry_path=f"s3://{S3_BUCKET}/{key}", status="pending"))
        session.commit()


class SelectedJob(BaseModel):
    selected: bool
    job_id: Optional[int]
    registry_path: Optional[str]
    info: str


@v1_router.post("/get_pending_job")
def get_pending_job(
    worker_id: str,
    auth: AuthToken = Depends(requires_permission(PermissionVariant.WORKER)),
) -> SelectedJob:
    with get_session() as session:
        for _ in range(5):
            job = session.exec(select(Jobs).where(Jobs.status == "pending").order_by(asc(Jobs.id)).limit(1)).first()

            if job is None:
                return SelectedJob(selected=False, job_id=None, registry_path=None, info="No pending jobs.")

            session.exec(
                update(Jobs)
                .where(Jobs.id == job.id)  # type: ignore
                .where(Jobs.status == "pending")  # type: ignore
                .values(status="processing")
                .values(worker_id=worker_id)
            )
            session.commit()

            # Check if we manage to grab this job
            final_job = session.exec(
                select(Jobs)
                .where(Jobs.id == job.id)
                .where(Jobs.status == "processing")
                .where(Jobs.worker_id == worker_id)
            ).first()

            if final_job is not None:
                return SelectedJob(
                    selected=True,
                    job_id=final_job.id,
                    registry_path=final_job.registry_path,
                    info="Job selected.",
                )

    return SelectedJob(selected=False, job_id=None, registry_path=None, info="Fail to select a job.")


@v1_router.post("/update_job")
async def update_job(
    auth: AuthToken = Depends(requires_permission(PermissionVariant.WORKER)), job_id: int = -1, result_json: str = ""
):
    with get_session() as session:
        result = session.exec(select(Jobs).where(Jobs.id == job_id)).first()
        if result is None:
            raise HTTPException(status_code=404, detail=f"Job with id `{job_id}` not found.")

        if result.status != "processing":
            raise HTTPException(
                status_code=400, detail=f"Job status is not `processing`, instead it is `{result.status}`."
            )
        session.exec(update(Jobs).where(Jobs.id == job_id).values(status="done", result=json.loads(result_json)))  # type: ignore
        session.commit()
