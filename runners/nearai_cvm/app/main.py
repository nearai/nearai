import io
import json
import logging
from typing import Dict, Optional

from dstack_sdk import TdxQuoteResponse  # type: ignore
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
from quote.quote import Quote  # type: ignore

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
    quote: Quote | None

    def __init__(self) -> None:  # noqa: D107
        self.agent = None
        self.assignment = None
        self.auth = None
        self.quote = None


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


class QuoteResponse(BaseModel):
    quote: str


@app.get("/quote", response_model=TdxQuoteResponse)
def get_quote(app_state: AppState = Depends(get_app_state)):
    if app_state.quote is None:
        app_state.quote = Quote()
    cmd = """echo | openssl s_client -connect localhost:443 2>/dev/null |\
     openssl x509 -pubkey -noout -outform DER | openssl dgst -sha256"""
    ssl_pub_key = subprocess.check_output(cmd, shell=True).decode("utf-8").split("= ")[1].strip()
    quote = app_state.quote.get_quote(ssl_pub_key)
    return quote


if __name__ == "__main__":
    import os
    import subprocess

    import uvicorn

    certs_dir = "/app/certs"
    key_path = os.path.join(certs_dir, "key.pem")
    cert_path = os.path.join(certs_dir, "cert.pem")

    # Create a config file for OpenSSL
    config_content = """[req]
distinguished_name = req_distinguished_name
x509_extensions = v3_req
prompt = no

[req_distinguished_name]
CN = localhost

[v3_req]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
IP.1 = 127.0.0.1
"""

    # Ensure the directory exists
    os.makedirs(certs_dir, exist_ok=True)

    # Write the OpenSSL config
    config_path = os.path.join(certs_dir, "openssl.cnf")
    with open(config_path, "w") as f:
        f.write(config_content)

    # Generate SSL certificate using OpenSSL with the config file
    openssl_cmd = [
        "openssl",
        "req",
        "-x509",
        "-newkey",
        "rsa:4096",
        "-keyout",
        key_path,
        "-out",
        cert_path,
        "-days",
        "365",
        "-nodes",
        "-config",
        config_path,
    ]

    try:
        subprocess.run(openssl_cmd, check=True)
        logger.info(f"SSL certificate generated at: {cert_path}")
        logger.info(f"SSL key generated at: {key_path}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error generating SSL certificate: {e}")

    # Clean up the config file
    try:
        os.remove(config_path)
    except Exception as e:
        logger.warning(f"Failed to remove OpenSSL config file: {e}")

    uvicorn.run(app, host="0.0.0.0", port=443, ssl_keyfile=key_path, ssl_certfile=cert_path)
