from enum import Enum

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select

from hub.api.v1.auth import AuthToken, get_auth
from hub.api.v1.models import Permissions, get_session

v1_router = APIRouter(
    prefix="/permissions",
    tags=["permissions"],
)


class PermissionVariant(str, Enum):
    UPDATE_PERMISSION = "update_permission"
    SUBMIT_JOB = "submit_job"
    WORKER = "worker"


def requires_permission(permission: PermissionVariant):
    def has_permission_inner(auth: AuthToken = Depends(get_auth)) -> AuthToken:
        with get_session() as session:
            result = session.exec(
                select(Permissions)
                .where(Permissions.account_id == auth.account_id)
                .where(Permissions.permission == permission)
            ).first()

            if result is None:
                raise HTTPException(status_code=403, detail=f"Permission denied. Missing permission `{permission}`")

        return auth

    return has_permission_inner


@v1_router.post("/grant_permission")
async def grant_permission(
    auth: AuthToken = Depends(requires_permission(PermissionVariant.UPDATE_PERMISSION)),
    account_id: str = "",
    permission: str = "",
):
    if account_id == "":
        raise HTTPException(status_code=400, detail="account_id is required")

    with get_session() as session:
        session.add(Permissions(account_id=account_id, permission=permission))
        session.commit()


@v1_router.post("/revoke_permission")
async def revoke_permission(
    auth: AuthToken = Depends(requires_permission(PermissionVariant.UPDATE_PERMISSION)),
    account_id: str = "",
    permission: str = "",
):
    if account_id == "":
        raise HTTPException(status_code=400, detail="account_id is required")

    with get_session() as session:
        if permission:
            session.delete(
                select(Permissions)
                .where(Permissions.account_id == account_id)
                .where(Permissions.permission == permission)
            )
        else:
            session.delete(select(Permissions).where(Permissions.account_id == account_id))
        session.commit()
