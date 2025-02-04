import io
import json
import logging
from typing import Dict, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from nearai.agents.agent import Agent  # type: ignore
from nearai.agents.environment import Environment  # type: ignore
from nearai.aws_runner.partial_near_client import PartialNearClient  # type: ignore
from nearai.shared.auth_data import AuthData  # type: ignore
from nearai.shared.client_config import ClientConfig  # type: ignore
from nearai.shared.inference_client import InferenceClient  # type: ignore
from nearai.shared.near.sign import verify_signed_message  # type: ignore
from pydantic import BaseModel
from quote.quote import Quote

bearer = HTTPBearer(auto_error=False)
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AssignRequest(BaseModel):
    agent_id: str
    thread_id: str
    api_url: str
    provider: str
    model: str
    temperature: float
    max_tokens: int
    max_iterations: int
    env_vars: Dict[str, str]


class AppState:
    assignment: AssignRequest | None
    agent: Agent | None
    auth: AuthData | None
    quote: Quote

    def __init__(self) -> None:  # noqa: D107
        self.agent = None
        self.assignment = None
        self.auth = None
        self.quote = Quote()


class RunRequest(BaseModel):
    run_id: str


class IsAssignedResp(BaseModel):
    is_assigned: bool


app.state.app_state = AppState()


def get_app_state() -> AppState:
    return app.state.app_state


# Configure logging
log_stream = io.StringIO()  # TODO: use rotating buffer?
stream_handler = logging.StreamHandler(log_stream)
stream_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.addHandler(stream_handler)
logger.addHandler(console_handler)


def assert_auth(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
    app_state: AppState = Depends(get_app_state),
):
    if auth is None:
        raise HTTPException(status_code=401, detail="No auth token provided")
    d = json.loads(auth.credentials)
    auth_object = AuthData(**d)
    if not auth_object:
        raise HTTPException(status_code=401, detail="No auth token provided")
    verification_result = verify_signed_message(
        auth_object.account_id,
        auth_object.public_key,
        auth_object.signature,
        auth_object.message,
        auth_object.nonce,
        auth_object.recipient,
        auth_object.callback_url,
    )
    if not verification_result:
        raise HTTPException(status_code=401, detail="Invalid auth token")

    if app_state.auth is not None:
        if app_state.auth.account_id != auth_object.account_id:
            """
            Ensures that the request is from the user assigned to the runner.
            """
            raise HTTPException(status_code=401, detail="Unauthorized")

    return auth_object


def init_runner(assignment: AssignRequest, auth: AuthData):
    logger.info(f"Starting download of agent: {assignment.agent_id}")

    client = PartialNearClient(assignment.api_url, auth)
    agent_files = client.get_agent(assignment.agent_id)
    agent_metadata = client.get_agent_metadata(assignment.agent_id)

    agent = Agent(assignment.agent_id, agent_files, agent_metadata)
    agent.model_provider = assignment.provider
    agent.model = assignment.model
    agent.model_temperature = assignment.temperature
    agent.model_max_tokens = assignment.max_tokens
    agent.max_iterations = assignment.max_iterations
    agent.env_vars = assignment.env_vars

    app.state.app_state.agent = agent


@app.post("/assign")
def assign(
    request: AssignRequest,
    auth: AuthData = Depends(assert_auth),
    app_state: AppState = Depends(get_app_state),
):
    if app_state.assignment is not None:
        raise HTTPException(status_code=409, detail="runner already assigned")

    app_state.assignment = request
    app_state.auth = auth

    logger.info(f"New assignment request for user {auth.account_id} with agent {request.agent_id}")

    init_runner(request, auth)

    return request


@app.post("/run")
def handler(
    request: RunRequest,
    auth: AuthData = Depends(assert_auth),
    app_state: AppState = Depends(get_app_state),
):
    if app_state.assignment is None:
        raise HTTPException(status_code=409, detail="No runner assigned")
    if app_state.agent is None:
        raise HTTPException(status_code=409, detail="Agent not downloaded")

    assignment = app_state.assignment
    agent = app_state.agent

    client_config = ClientConfig(
        base_url=assignment.api_url + "/v1",
        auth=auth,
    )
    inference_client = InferenceClient(client_config)
    hub_client = client_config.get_hub_client()
    env = Environment(
        path=agent.temp_dir,
        agents=[agent],
        client=inference_client,
        hub_client=hub_client,
        thread_id=assignment.thread_id,
        run_id=request.run_id,
        env_vars=assignment.env_vars,
        print_system_log=False,
    )
    if agent.welcome_title:
        print(agent.welcome_title)
    if agent.welcome_description:
        print(agent.welcome_description)
    env.run("", agent.max_iterations)


@app.get("/logs")
def get_logs(
    auth: AuthData = Depends(assert_auth),
):
    """Return all logged messages."""
    return {"logs": log_stream.getvalue()}


@app.get("/is_assigned")
def is_assigned(app_state: AppState = Depends(get_app_state)):
    is_assigned = app_state.assignment is not None
    return IsAssignedResp(is_assigned=is_assigned)


@app.get("/quote")
def get_quote(app_state: AppState = Depends(get_app_state)):
    return app_state.quote.get_quote()
