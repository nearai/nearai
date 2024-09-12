import logging

from dotenv import load_dotenv
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from hub.api.v1.agent_routes import v1_router as agent_router
from hub.api.v1.benchmark import v1_router as benchmark_router
from hub.api.v1.exceptions import TokenValidationError
from hub.api.v1.files import files_router
from hub.api.v1.registry import v1_router as registry_router
from hub.api.v1.routes import v1_router
from hub.api.v1.stars import v1_router as stars_router
from hub.api.v1.vector_stores import vector_stores_router

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()
app = FastAPI()

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
app.include_router(agent_router, prefix="/v1")
app.include_router(benchmark_router, prefix="/v1")
app.include_router(vector_stores_router, prefix="/v1")
app.include_router(files_router, prefix="/v1")
app.include_router(stars_router, prefix="/v1")


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
