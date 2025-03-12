from fastapi import APIRouter, Depends, Form, HTTPException
from sqlmodel import select

from hub.api.v1.auth import AuthToken, get_auth
from hub.api.v1.models import Stars, get_session

v1_router = APIRouter(
    prefix="/stars",
    tags=["stars"],
)


@v1_router.post("/add_star")
async def add_star(auth: AuthToken = Depends(get_auth), namespace: str = Form(...), name: str = Form(...)):
    with get_session() as session:
        result = session.exec(
            select(Stars).where(Stars.account_id == auth.account_id, Stars.namespace == namespace, Stars.name == name)
        ).first()

        if result is not None:
            raise HTTPException(status_code=400, detail="Already starred")

        session.add(Stars(account_id=auth.account_id, namespace=namespace, name=name))
        session.commit()


@v1_router.post("/remove_star")
async def remove_star(auth: AuthToken = Depends(get_auth), namespace: str = Form(...), name: str = Form(...)):
    with get_session() as session:
        result = session.exec(
            select(Stars).where(Stars.account_id == auth.account_id, Stars.namespace == namespace, Stars.name == name)
        ).first()

        if result is None:
            raise HTTPException(status_code=400, detail="Not starred")

        session.delete(result)
        session.commit()
