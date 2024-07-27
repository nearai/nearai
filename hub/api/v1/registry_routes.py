from hub.api.v1.auth import get_current_user, AuthToken
from fastapi import APIRouter, HTTPException, Depends
from nearai.registry import registry

v1_router = APIRouter(
    prefix="/registry",
    tags=["registry"],
)


@v1_router.get("/download/{name}")
def get_item(name: str, auth: AuthToken = Depends(get_current_user)):
    file = registry.get_file(name)
    if file is None:
        raise HTTPException(status_code=404, detail="File not found")
    return file


@v1_router.get("/agents/{name}")
def get_agent(name: str, auth: AuthToken = Depends(get_current_user)):
    file = registry.get_file(name, file="agent.py")
    if file is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return file
