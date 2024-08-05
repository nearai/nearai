from fastapi import APIRouter, Depends, HTTPException
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
