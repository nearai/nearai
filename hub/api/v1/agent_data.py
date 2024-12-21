import sys
from typing import Any, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import select

from hub.api.v1.auth import AuthToken, get_auth
from hub.api.v1.models import AgentData, get_session

agent_data_router = APIRouter(
    tags=["agents, assistants"],
)


class AgentDataRequest(BaseModel):
    namespace: str
    name: str
    key: str
    value: Union[str, dict[Any, Any]]


def is_hub_account(auth: AuthToken):
    return False  # todo implement


@agent_data_router.post("/agent_data/", response_model=AgentData)
def save_agent_data(request_data: AgentDataRequest, auth: AuthToken = Depends(get_auth)):
    if not (auth.account_id == request_data.namespace) and not is_hub_account(auth):
        raise HTTPException(status_code=403, detail="Not authorized to store data for this agent")

    # 10KB max size per entry
    if sys.getsizeof(request_data.value) > 10240:
        raise HTTPException(status_code=400, detail="Value is too large, must be less than 10KB")

    with get_session() as session:
        agent_data = session.exec(
            select(AgentData).where(
                AgentData.namespace == request_data.namespace,
                AgentData.name == request_data.name,
                AgentData.key == request_data.key,
            )
        ).first()

        if agent_data:
            agent_data.value = request_data.value
        else:
            agent_data = AgentData(
                namespace=request_data.namespace, name=request_data.name, key=request_data.key, value=request_data.value
            )
            session.add(agent_data)

        session.commit()
        return agent_data


@agent_data_router.get("/agent_data/{namespace}/{name}", response_model=List[AgentData])
def get_agent_data(namespace: str, name: str, auth: AuthToken = Depends(get_auth)):
    if not (auth.account_id == namespace) and not is_hub_account(auth):
        raise HTTPException(status_code=403, detail="Not authorized to retrieve data for this agent")

    with get_session() as session:
        agent_data = session.query(AgentData).filter_by(namespace=namespace, name=name).all()
        return agent_data


@agent_data_router.get("/agent_data/{namespace}/{name}/{key}", response_model=Optional[AgentData])
def get_agent_data_by_key(namespace: str, name: str, key: str, auth: AuthToken = Depends(get_auth)):
    if not (auth.account_id == namespace) and not is_hub_account(auth):
        raise HTTPException(status_code=403, detail="Not authorized to retrieve data for this agent")

    with get_session() as session:
        agent_data = session.query(AgentData).filter_by(namespace=namespace, name=name, key=key).first()
        if not agent_data:
            return None
        return agent_data
