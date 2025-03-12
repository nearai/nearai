from typing import Dict, List

from fastapi import APIRouter, Depends
from sqlmodel import asc, select

from hub.api.v1.auth import AuthToken, get_auth
from hub.api.v1.models import Log, get_session

logs_router = APIRouter(
    prefix="/logs",
    tags=["logs"],
)


@logs_router.post("/add_log")
async def add_log(target: str, info: Dict, auth: AuthToken = Depends(get_auth)) -> Log:
    with get_session() as session:
        log = Log(
            account_id=auth.account_id,
            target=target,
            info=info,
        )
        session.add(log)
        session.commit()
        session.refresh(log)
        return log


@logs_router.get("/get_logs")
async def get_logs(
    target: str,
    after_id: int,
    limit: int,
    auth: AuthToken = Depends(get_auth),
) -> List[Log]:
    with get_session() as session:
        query = (
            select(Log)
            .where(Log.account_id == auth.account_id)
            .where(Log.id > after_id)
            .where(Log.target == target)
            .order_by(asc(Log.id))
            .limit(limit)
        )
        result = list(session.exec(query).all())
        return result
