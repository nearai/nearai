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
