from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from nearai.agent import AGENT_FILENAME
from nearai.registry import registry

from hub.api.v1.auth import AuthToken, revokable_auth

v1_router = APIRouter(
    prefix="/registry",
    tags=["registry"],
)


@v1_router.get("/download/{name}")
def get_item(name: str, auth: AuthToken = Depends(revokable_auth)):
    file = registry.get_file(name)
    if file is None:
        raise HTTPException(status_code=404, detail="File not found")
    return file


@v1_router.get("/agents/{name}")
def get_agent(name: str, auth: AuthToken = Depends(revokable_auth)):
    file = registry.get_file(name, file=AGENT_FILENAME)
    if file is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return file


@v1_router.get(
    "/environments/{id}",
    responses={200: {"content": {"application/gzip": {"schema": {"type": "string", "format": "binary"}}}}},
)
def get_environment(id: str, auth: AuthToken = Depends(revokable_auth)):
    env = registry.get_file(id)
    if env is None:
        raise HTTPException(status_code=404, detail="Environment not found")
    headers = {"Content-Disposition": "attachment; filename=environment.tar.gz"}
    return Response(env, headers=headers, media_type="application/gzip")


@v1_router.post("/environments")
async def save_environment(
    env_id: str,
    file: UploadFile = File(...),
    name: Optional[str] = None,
    description: Optional[str] = None,
    details: Optional[dict] = None,
    tags: Optional[List[str]] = None,
    auth: AuthToken = Depends(revokable_auth),
):
    """Save environment to registry.

    :param env_id: An uuid for the run
    :param file: A tar.gz file containing the environment files
    :param name: An optional name for the run
    :param description: An optional description for the run
    :param details: An optional dictionary of details for the run such as:
    base_id (the environment env_id before the latest changes),
    timestamp,
    agents (which agents were made available to the run),
    run_type
    :param tags:
    :param auth: This endpoint requires authentication
    :return: The registry_id of the saved environment.
    """
    if not env_id:
        raise HTTPException(status_code=400, detail="Run ID is required")
    if len(env_id) < 32 or len(env_id) > 64 or not env_id.isalnum():
        raise HTTPException(status_code=400, detail="Invalid Run ID")

    s3_path = f"environments/{env_id}"
    author = auth.account_id

    all_tags = tags or ["environment"]
    if "environment" not in all_tags:
        all_tags.append("environment")

    registry_id = registry.upload(
        file_obj=file,
        s3_path=s3_path,
        author=author,
        description=description,
        name=name,
        details=details,
        show_entry=True,
        tags=all_tags,
    )
    return {"info": "Environment saved successfully", "registry_id": registry_id}
