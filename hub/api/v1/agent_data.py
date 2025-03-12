import json
import sys
from os import getenv
from typing import Any, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import select

from hub.api.v1.auth import AuthToken, get_auth
from hub.api.v1.entry_location import EntryLocation
from hub.api.v1.models import AgentData, get_session
from hub.api.v1.sign import is_trusted_runner_api_key

agent_data_router = APIRouter(
    tags=["agents, assistants"],
)


class AgentDataRequest(BaseModel):
    key: str
    value: Union[dict[Any, Any]]


@agent_data_router.post("/agent_data", response_model=AgentData)
def save_agent_data(request_data: AgentDataRequest, auth: AuthToken = Depends(get_auth)):
    agent = agent_from_trusted_runner_data(auth)

    # 10KB max size per entry
    if sys.getsizeof(request_data.value) > 10240:
        raise HTTPException(status_code=400, detail="Value is too large, must be less than 10KB")

    namespace = agent.namespace
    name = agent.name

    with get_session() as session:
        agent_data = session.exec(
            select(AgentData).where(
                AgentData.namespace == namespace,
                AgentData.name == name,
                AgentData.key == request_data.key,
            )
        ).first()

        if agent_data:
            agent_data.value = request_data.value
        else:
            agent_data = AgentData(namespace=namespace, name=name, key=request_data.key, value=request_data.value)
            session.add(agent_data)

        session.commit()
        return agent_data


def agent_from_trusted_runner_data(auth) -> EntryLocation:
    """If a trusted runner API key was passed, extract agent data from auth, otherwise, raise an error."""
    runner_data = json.loads(auth.runner_data or "{}")
    agent = runner_data.get("agent", None)
    runner_api_key = runner_data.get("runner_api_key", None)
    runner_env = getenv("RUNNER_ENVIRONMENT", "local_runner")
    if runner_env != "local_runner":
        if not runner_api_key or not is_trusted_runner_api_key(runner_api_key):
            raise HTTPException(status_code=403, detail="Not authorized to store data for this agent")
    if not agent:
        raise HTTPException(status_code=400, detail="Agent data missing")
    return EntryLocation.from_str(agent)


@agent_data_router.get("/agent_data", response_model=List[AgentData])
def get_agent_data(auth: AuthToken = Depends(get_auth)) -> List[AgentData]:
    agent = agent_from_trusted_runner_data(auth)

    return _fetch_agent_data(agent.namespace, agent.name)


def _fetch_agent_data(namespace, name):
    with get_session() as session:
        agent_data = session.query(AgentData).filter_by(namespace=namespace, name=name).all()
        return agent_data


@agent_data_router.get("/agent_data/{key}", response_model=Optional[AgentData])
def get_agent_data_by_key(key: str, auth: AuthToken = Depends(get_auth)) -> Optional[AgentData]:
    agent = agent_from_trusted_runner_data(auth)
    return _fetch_agent_data_by_key(agent.namespace, agent.name, key)


def _fetch_agent_data_by_key(namespace, name, key):
    with get_session() as session:
        agent_data = session.query(AgentData).filter_by(namespace=namespace, name=name, key=key).first()
        if not agent_data:
            return None
        return agent_data


@agent_data_router.get("/agent_data_admin/{namespace}/{name}", response_model=List[AgentData])
def get_agent_data_for_author(namespace: str, name: str, auth: AuthToken = Depends(get_auth)) -> List[AgentData]:
    if not (auth.account_id == namespace):
        raise HTTPException(status_code=403, detail="Not authorized to retrieve data for this agent")

    return _fetch_agent_data(namespace, name)


@agent_data_router.get("/agent_data_admin/{namespace}/{name}/{key}", response_model=Optional[AgentData])
def get_agent_data_by_key_for_author(
    namespace: str, name: str, key: str, auth: AuthToken = Depends(get_auth)
) -> Optional[AgentData]:
    if not (auth.account_id == namespace):
        raise HTTPException(status_code=403, detail="Not authorized to retrieve data for this agent")

    return _fetch_agent_data_by_key(namespace, name, key)
