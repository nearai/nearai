import importlib.metadata
import json
import logging
import time
from typing import Any, Dict, Iterable, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import HTTPBearer
from pydantic import BaseModel, field_validator
from shared.near.primitives import PROVIDER_MODEL_SEP, get_provider_model

from hub.api.v1.auth import AuthToken, revokable_auth, validate_signature
from hub.api.v1.completions import Message, Provider, get_llm_ai, handle_stream
from hub.api.v1.sql import SqlClient

v1_router = APIRouter()
db = SqlClient()
logger = logging.getLogger(__name__)
security = HTTPBearer()


REVOKE_MESSAGE = "Are you sure? Revoking a nonce"
REVOKE_ALL_MESSAGE = "Are you sure? Revoking all nonces"


class ResponseFormat(BaseModel):
    """The format of the response."""

    type: str
    """The type of the response format."""
    json_schema: Optional[Dict] = None
    """Optional JSON schema for the response format."""


class LlmRequest(BaseModel):
    """Base class for LLM requests."""

    model: str = f"fireworks{PROVIDER_MODEL_SEP}accounts/fireworks/models/mixtral-8x22b-instruct"
    """The model to use for generation."""
    provider: Optional[str] = "fireworks"
    """The provider to use for generation."""
    max_tokens: Optional[int] = 1024
    """The maximum number of tokens to generate."""
    logprobs: Optional[int] = None
    """The log probabilities of the generated tokens."""
    temperature: float = 1.0
    """The temperature for sampling."""
    top_p: float = 1.0
    """The top-p value for nucleus sampling."""
    frequency_penalty: Optional[float] = 0.0
    """The frequency penalty."""
    n: int = 1
    """The number of completions to generate."""
    stop: Optional[Union[str, List[str]]] = None
    """The stop sequence(s) for generation."""
    response_format: Optional[ResponseFormat] = None
    """The format of the response."""
    stream: bool = False
    """Whether to stream the response."""
    tools: Optional[List] = None

    @field_validator("model")
    @classmethod
    def validate_model(cls, value: str):  # noqa: D102
        if PROVIDER_MODEL_SEP not in value:
            value = f"fireworks{PROVIDER_MODEL_SEP}accounts/fireworks/models/{value}"
        return value


class CompletionsRequest(LlmRequest):
    """Request for completions."""

    prompt: str


class ChatCompletionsRequest(LlmRequest):
    """Request for chat completions."""

    messages: List[Message]


class EmbeddingsRequest(BaseModel):
    """Request for embeddings."""

    input: str | List[str] | Iterable[int] | Iterable[Iterable[int]]
    model: str = f"fireworks{PROVIDER_MODEL_SEP}nomic-ai/nomic-embed-text-v1.5"
    provider: Optional[str] = None


# The request might come as provider::model
# OpenAI API specs expects model name to be only the model name, not provider::model
def convert_request(request: ChatCompletionsRequest | CompletionsRequest | EmbeddingsRequest):
    provider, model = get_provider_model(request.provider, request.model)
    request.model = model
    request.provider = provider
    if request.model is None or request.provider is None:
        raise HTTPException(status_code=400, detail="Invalid model or provider")
    return request


@v1_router.post("/completions")
async def completions(
    request: CompletionsRequest = Depends(convert_request), auth: AuthToken = Depends(revokable_auth)
):
    logger.info(f"Received completions request: {request.model_dump()}")

    try:
        assert request.provider is not None
        llm = get_llm_ai(request.provider)
    except NotImplementedError:
        raise HTTPException(status_code=400, detail="Provider not supported") from None

    resp = await llm.completions.create(**request.model_dump(exclude={"provider", "response_format"}))

    if request.stream:

        def add_usage_callback(response_text):
            logger.info("Stream done, adding usage to database")
            db.add_user_usage(
                auth.account_id, request.prompt, response_text, request.model, request.provider, "/completions"
            )

        return StreamingResponse(handle_stream(resp, add_usage_callback), media_type="text/event-stream")
    else:
        c = json.dumps(resp.model_dump())

        db.add_user_usage(auth.account_id, request.prompt, c, request.model, request.provider, "/completions")

        return JSONResponse(content=json.loads(c))


@v1_router.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionsRequest = Depends(convert_request), auth: AuthToken = Depends(revokable_auth)
):
    logger.info(f"Received chat completions request: {request.model_dump()}")

    try:
        assert request.provider is not None
        llm = get_llm_ai(request.provider)
    except NotImplementedError:
        raise HTTPException(status_code=400, detail="Provider not supported") from None

    try:
        resp = await llm.chat.completions.create(**request.model_dump(exclude={"provider"}))
    except Exception as e:
        error_message = str(e)
        if "Error code: 404" in error_message and "Model not found, inaccessible, and/or not deployed" in error_message:
            raise HTTPException(status_code=400, detail="Model not supported") from None
        else:
            raise HTTPException(status_code=400, detail=error_message) from None

    if request.stream:

        def add_usage_callback(response_text):
            logger.info("Stream done, adding usage to database")
            db.add_user_usage(
                auth.account_id,
                json.dumps([x.model_dump() for x in request.messages]),
                response_text,
                request.model,
                request.provider,
                "/chat/completions",
            )

        return StreamingResponse(handle_stream(resp, add_usage_callback), media_type="text/event-stream")

    else:
        c = json.dumps(resp.model_dump())
        db.add_user_usage(
            auth.account_id,
            json.dumps([x.model_dump() for x in request.messages]),
            c,
            request.model,
            request.provider,
            "/chat/completions",
        )

        return JSONResponse(content=json.loads(c))


@v1_router.get("/models")
async def get_models() -> JSONResponse:
    all_models: List[Dict[str, Any]] = []

    for p in Provider:
        try:
            provider_models = await get_llm_ai(p.value).models.list()
            for model in provider_models.data:
                model_dict = model.model_dump()
                model_dict["id"] = f"{p.value}{PROVIDER_MODEL_SEP}{model_dict['id']}"
                all_models.append(model_dict)
        except Exception as e:
            logger.error(f"Error getting models from provider {p.value}: {e}")

    # Format the response to match OpenAI API structure
    response = {"object": "list", "data": all_models}

    return JSONResponse(content=response)


@v1_router.post("/embeddings")
async def embeddings(request: EmbeddingsRequest = Depends(convert_request), auth: AuthToken = Depends(revokable_auth)):
    logger.info(f"Received embeddings request: {request.model_dump()}")

    try:
        assert request.provider is not None
        llm = get_llm_ai(request.provider)
    except NotImplementedError:
        raise HTTPException(status_code=400, detail="Provider not supported") from None

    resp = await llm.embeddings.create(**request.model_dump(exclude={"provider"}))

    c = json.dumps(resp.model_dump())
    db.add_user_usage(auth.account_id, str(request.input), c, request.model, request.provider, "/embeddings")

    return JSONResponse(content=json.loads(c))


class RevokeNonce(BaseModel):
    nonce: bytes
    """The nonce to revoke."""

    @field_validator("nonce")
    @classmethod
    def validate_and_convert_nonce(cls, value: str):  # noqa: D102
        if len(value) != 32:
            raise ValueError("Invalid nonce, must of length 32")
        return value


@v1_router.post("/nonce/revoke")
async def revoke_nonce(nonce: RevokeNonce, auth: AuthToken = Depends(validate_signature)):
    """Revoke a nonce for the account."""
    logger.info(f"Received request to revoke nonce {nonce} for account {auth.account_id}")
    if auth.message != REVOKE_MESSAGE:
        raise HTTPException(status_code=401, detail="Invalid nonce revoke message")

    await verify_revoke_nonce(auth)

    db.revoke_nonce(auth.account_id, nonce.nonce)
    return JSONResponse(content={"message": f"Nonce {nonce} revoked"})


@v1_router.post("/nonce/revoke/all")
async def revoke_all_nonces(auth: AuthToken = Depends(validate_signature)):
    """Revoke all nonces for the account."""
    logger.info(f"Received request to revoke all nonces for account {auth.account_id}")
    if auth.message != REVOKE_ALL_MESSAGE:
        raise HTTPException(status_code=401, detail="Invalid nonce revoke message")

    await verify_revoke_nonce(auth)

    db.revoke_all_nonces(auth.account_id)
    return JSONResponse(content={"message": "All nonces revoked"})


@v1_router.get("/nonce/list")
async def list_nonces(auth: AuthToken = Depends(revokable_auth)):
    """List all nonces for the account."""
    nonces = db.get_account_nonces(auth.account_id)
    res = nonces.model_dump_json()
    logger.info(f"Listing nonces for account {auth.account_id}: {res}")
    return JSONResponse(content=json.loads(res))


async def verify_revoke_nonce(auth):
    """If signature is too old, request will be rejected."""
    ts = int(auth.nonce)
    now = int(time.time() * 1000)
    if now - ts > 5 * 60 * 1000:
        raise HTTPException(status_code=401, detail="Invalid nonce")


@v1_router.get("/version")
async def version() -> str:
    return importlib.metadata.version("nearai")
