# ruff: noqa: E402  # two blocks of imports makes the linter sad
import logging
import os

from ddtrace import patch_all
from dotenv import load_dotenv

# Initialize env vars, logging, and Datadog tracing before any other imports
load_dotenv()

if os.environ.get("DD_ENABLED"):
    patch_all()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# next round of imports

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from hub.api.v1.agent_data import agent_data_router
from hub.api.v1.agent_routes import run_agent_router
from hub.api.v1.benchmark import v1_router as benchmark_router
from hub.api.v1.delegation import v1_router as delegation_router
from hub.api.v1.evaluation import v1_router as evaluation_router
from hub.api.v1.exceptions import TokenValidationError
from hub.api.v1.files import files_router
from hub.api.v1.hub_secrets import hub_secrets_router
from hub.api.v1.jobs import v1_router as job_router
from hub.api.v1.logs import logs_router
from hub.api.v1.permissions import v1_router as permission_router
from hub.api.v1.quote import quote_router
from hub.api.v1.registry import v1_router as registry_router
from hub.api.v1.routes import v1_router
from hub.api.v1.scheduled_run import scheduled_run_router
from hub.api.v1.stars import v1_router as stars_router
from hub.api.v1.thread_routes import threads_router
from hub.api.v1.vector_stores import vector_stores_router

# No lifespan function - FastAPI will use default behavior
app = FastAPI(docs_url="/docs/hub/interactive", redoc_url="/docs/hub/reference")

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router, prefix="/v1")
app.include_router(registry_router, prefix="/v1")
app.include_router(run_agent_router, prefix="/v1")
app.include_router(agent_data_router, prefix="/v1")
app.include_router(benchmark_router, prefix="/v1")
app.include_router(stars_router, prefix="/v1")
app.include_router(job_router, prefix="/v1")
app.include_router(permission_router, prefix="/v1")
app.include_router(evaluation_router, prefix="/v1")
app.include_router(delegation_router, prefix="/v1")
app.include_router(logs_router, prefix="/v1")
app.include_router(quote_router, prefix="/v1")

# TODO: OpenAPI can't be generated for the following routes.
app.include_router(vector_stores_router, prefix="/v1")
app.include_router(files_router, prefix="/v1")
app.include_router(threads_router, prefix="/v1")
app.include_router(hub_secrets_router, prefix="/v1")
app.include_router(scheduled_run_router, prefix="/v1")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.exception_handler(TokenValidationError)
async def token_validation_exception_handler(request: Request, exc: TokenValidationError):
    exc_lines = exc.detail.split("\n")
    exc_str = f"{exc_lines[0]}: {exc_lines[1]}.{exc_lines[2]}".replace("  ", " ") if len(exc_lines) > 2 else ""
    logger.info(f"Received invalid Auth Token. {exc_str}")
    # 400 Bad Request if auth request was invalid
    content = {"status_code": 400, "message": exc_str, "data": None}
    return JSONResponse(content=content, status_code=status.HTTP_400_BAD_REQUEST)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    exc_str = f"{exc}".replace("\n", " ").replace("   ", " ")
    content = {"status_code": 422, "message": exc_str, "data": None}
    return JSONResponse(content=content, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


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
DNS.1 = cvm.near.ai
DNS.2 = localhost
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
