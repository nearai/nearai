import asyncio
import datetime
import os
import signal
import subprocess
from datetime import timedelta
from os import getenv
from pathlib import Path
from typing import Optional

import httpx
import typer
import uvicorn
from fastapi import FastAPI, HTTPException
from nearai.config import CONFIG, save_config_file
from nearai.delegation import OnBehalfOf
from nearai.jobs import JobsApi
from nearai.lib import parse_location
from nearai.openapi_client.api.delegation_api import DelegationApi
from nearai.openapi_client.api.jobs_api import WorkerKind
from nearai.openapi_client.models.entry_location import EntryLocation
from nearai.openapi_client.models.job import Job
from nearai.openapi_client.models.job_status import JobStatus
from nearai.registry import registry
from nearai.shared.auth_data import AuthData
from pydantic import BaseModel

app = typer.Typer()
loop = asyncio.get_event_loop()

WORKER_KIND = WorkerKind(getenv("WORKER_KIND"))
WORKER_PORT = int(getenv("WORKER_PORT", 8000))
WORKER_SLEEP_TIME = int(getenv("WORKER_SLEEP_TIME", 1))
WORKER_URL = getenv("WORKER_URL", f"http://worker:{WORKER_PORT}")
WORKER_JOB_TIMEOUT = int(getenv("WORKER_JOB_TIMEOUT", 60 * 60 * 6))  # 6 hours
WORKER_ACCOUNT_ID = getenv("NEARAIWORKER_ACCOUNT_ID", "nearaiworker.near")
WORKER_SIGNATURE = getenv("NEARAIWORKER_SIGNATURE")

JOB_DIR = Path("~/job/")
JOBS_API = JobsApi()
DELEGATION_API = DelegationApi()

SCHEDULER_ACCOUNT_ID = getenv("NEARAISCHEDULER_ACCOUNT_ID", "nearaischeduler.near")


class SetupParams(BaseModel):
    auth_data: AuthData
    on_behalf_of: str


class ResultJson(BaseModel):
    output: str


class JobResult(BaseModel):
    stdout: str
    stderr: str
    return_code: int


def try_parse_location(location: str) -> Optional[EntryLocation]:
    try:
        return parse_location(location)
    except Exception:
        return None


async def run_scheduler():
    while True:
        try:
            await asyncio.sleep(WORKER_SLEEP_TIME)
            async with httpx.AsyncClient() as client:
                ## Poll worker health
                try:
                    response = await client.get(WORKER_URL + "/health")
                    if response.status_code != 200:
                        print("Worker is not healthy ... retrying")
                        continue
                except Exception as e:
                    print(f"Couldn't reach worker: {e}\nRetrying...")
                    continue

                ## Get pending jobs
                selected_job = JOBS_API.get_pending_job_v1_jobs_get_pending_job_post(
                    worker_id=SCHEDULER_ACCOUNT_ID,
                    worker_kind=WORKER_KIND,
                )
                if not selected_job:
                    print("No pending jobs ... retrying")
                    continue

                if not selected_job.selected:
                    print(selected_job)
                    print(f"Job is not selected: {selected_job.job}")
                    continue
                if not selected_job.job:
                    print(selected_job)
                    print(f"No job included in the response: {selected_job.job}")
                    continue
                if not selected_job.registry_path:
                    print(f"Job has no registry path: {selected_job.job}")
                    JOBS_API.update_job_v1_jobs_update_job_post(
                        job_id=selected_job.job.id,
                        status=JobStatus.COMPLETED,
                        result_json=ResultJson(output="No registry path").model_dump_json(),
                    )
                    continue
                location = try_parse_location(selected_job.registry_path)
                if not location:
                    print(f"Failed to parse registry path: {selected_job.registry_path} ... retrying")
                    JOBS_API.update_job_v1_jobs_update_job_post(
                        job_id=selected_job.job.id,
                        status=JobStatus.COMPLETED,
                        result_json=ResultJson(output="Failed to parse registry path").model_dump_json(),
                    )
                    continue

                ## Delegate to the worker as the user
                try:
                    with OnBehalfOf(selected_job.job.account_id):
                        DELEGATION_API.delegate_v1_delegation_delegate_post(
                            delegate_account_id=WORKER_ACCOUNT_ID,
                            expires_at=datetime.datetime.now() + timedelta(days=1),
                        )
                except Exception as e:
                    JOBS_API.update_job_v1_jobs_update_job_post(
                        job_id=selected_job.job.id,
                        status=JobStatus.COMPLETED,
                        result_json=ResultJson(output=f"Failed to download/delegate job: {e}").model_dump_json(),
                    )
                    with OnBehalfOf(selected_job.job.account_id):
                        DELEGATION_API.revoke_delegation_v1_delegation_revoke_delegation_post(
                            delegate_account_id=WORKER_ACCOUNT_ID
                        )
                    print(f"Failed to download job: {e}")
                    continue

                ## Execute the job
                success = False
                job = selected_job.job
                try:
                    response = await client.post(
                        WORKER_URL + "/execute",
                        json=job.model_dump(),
                        timeout=WORKER_JOB_TIMEOUT,
                    )
                    if response.status_code != 200:
                        raise Exception(response.text)

                    success = True
                    response_json = response.json()
                    job_result = JobResult(**response_json)
                except Exception as e:
                    JOBS_API.update_job_v1_jobs_update_job_post(
                        job_id=selected_job.job.id,
                        status=JobStatus.COMPLETED,
                        result_json=ResultJson(output=f"Failed to execute job: {e}").model_dump_json(),
                    )
                    print(f"Failed to execute job: {e}")

                ## cleanup
                if success:
                    JOBS_API.update_job_v1_jobs_update_job_post(
                        job_id=selected_job.job.id,
                        status=JobStatus.COMPLETED,
                        result_json=ResultJson(output=job_result.model_dump_json()).model_dump_json(),
                    )

                ## Revoke access of the worker from the scheduler
                try:
                    with OnBehalfOf(selected_job.job.account_id):
                        DELEGATION_API.revoke_delegation_v1_delegation_revoke_delegation_post(
                            delegate_account_id=WORKER_ACCOUNT_ID
                        )
                        DELEGATION_API.revoke_delegation_v1_delegation_revoke_delegation_post(
                            delegate_account_id=SCHEDULER_ACCOUNT_ID
                        )
                except Exception as e:
                    print(f"Failed to revoke delegation: {e}")
                    continue

                ## kill the worker
                try:
                    await client.post(WORKER_URL + "/reset")
                except Exception as e:
                    print(f"Error: {e}")
        except Exception as e:
            print(f"Error: {e}")


def run_worker():
    app = FastAPI()
    current_job = None

    @app.post("/reset")
    def reset():
        os.kill(os.getpid(), signal.SIGTERM)

    @app.get("/health")
    async def health():
        return "OK"

    @app.get("/current_job")
    async def get_current_job() -> Optional[Job]:
        return current_job

    @app.post("/execute")
    def execute(job: Job) -> JobResult:
        nonlocal current_job
        print(f"Received job: {job}")

        # Let the worker download the job on behalf of the user
        with OnBehalfOf(job.account_id):
            downloaded = registry.download(job.registry_path)

        ## Update auth so all actions are executed by the worker
        ## on behalf of the user
        assert CONFIG.auth, "Auth data is not set"
        CONFIG.auth.on_behalf_of = job.account_id
        save_config_file(CONFIG.model_dump())

        ## save current job
        current_job = job

        try:
            # Execute the run.sh script in a subprocess
            env = {
                "http_proxy": "http://proxy:8888",
                "https_proxy": "http://proxy:8888",
                "HTTP_PROXY": "http://proxy:8888",
                "HTTPS_PROXY": "http://proxy:8888",
                **os.environ,
            }
            result = subprocess.run(
                ["bash", "run.sh"],
                cwd=downloaded.as_posix(),
                capture_output=True,
                timeout=WORKER_JOB_TIMEOUT,
                env=env,
            )

            ## cleanup
            current_job = None  # noqa: F841
            try:
                return JobResult(
                    stdout=result.stdout.decode(), stderr=result.stderr.decode(), return_code=result.returncode
                )
            except Exception as e:
                return JobResult(stdout="", stderr=str(e), return_code=1)
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=500, detail="Execution timed out.")  # noqa: B904

    uvicorn.run(app, host="0.0.0.0", port=WORKER_PORT)


@app.command()
def scheduler():
    loop.run_until_complete(run_scheduler())


@app.command()
def worker():
    run_worker()


if __name__ == "__main__":
    app()
