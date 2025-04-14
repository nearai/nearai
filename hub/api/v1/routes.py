import importlib.metadata
import json
import logging
import time
from typing import Annotated, Iterable, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import HTTPBearer
from nearai.shared.cache import mem_cache_with_timeout
from nearai.shared.client_config import DEFAULT_TIMEOUT
from nearai.shared.near.sign import derive_new_extended_private_key, get_public_key
from nearai.shared.provider_models import PROVIDER_MODEL_SEP, get_provider_model
from openai.types.beta.assistant_response_format_option import AssistantResponseFormatOption
from pydantic import BaseModel, field_validator

from hub.api.v1.auth import AuthToken, get_auth, validate_signature
from hub.api.v1.completions import Message, Provider, get_llm_ai, handle_stream
from hub.api.v1.images import get_images_ai
from hub.api.v1.sign import get_hub_key, get_signed_completion, is_trusted_runner_api_key
from hub.api.v1.sql import SqlClient

v1_router = APIRouter()
logger = logging.getLogger(__name__)
security = HTTPBearer()


def get_db() -> SqlClient:
    """Get a thread-local database connection."""
    return SqlClient()


DatabaseSession = Annotated[SqlClient, Depends(get_db)]


REVOKE_MESSAGE = "Are you sure? Revoking a nonce"
REVOKE_ALL_MESSAGE = "Are you sure? Revoking all nonces"


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
    response_format: Optional[AssistantResponseFormatOption] = None
    """The format of the response."""
    stream: bool = False
    """Whether to stream the response."""
    tools: Optional[List] = []

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

    input: Union[str, List[str], Iterable[int], Iterable[Iterable[int]]]
    model: str = f"fireworks{PROVIDER_MODEL_SEP}nomic-ai/nomic-embed-text-v1.5"
    provider: Optional[str] = None


class ImageGenerationRequest(BaseModel):
    """Request for image generation."""

    prompt: str
    """A text description of the desired image(s)."""
    model: str = f"fireworks{PROVIDER_MODEL_SEP}accounts/fireworks/models/playground-v2-5-1024px-aesthetic"
    provider: Optional[str] = None
    init_image: Optional[str] = None
    image_strength: Optional[float] = None
    control_image: Optional[str] = None
    control_net_name: Optional[str] = None
    conditioning_scale: Optional[float] = None
    cfg_scale: Optional[float] = None
    sampler: Optional[str] = None
    steps: Optional[int] = None
    seed: Optional[int] = 0

    @field_validator("model")
    @classmethod
    def validate_model(cls, value: str):  # noqa: D102
        if PROVIDER_MODEL_SEP not in value:
            value = f"fireworks{PROVIDER_MODEL_SEP}accounts/fireworks/models/{value}"
        return value


# The request might come as provider::model
# OpenAI API specs expects model name to be only the model name, not provider::model
def convert_request(
    request: Union[ChatCompletionsRequest, CompletionsRequest, EmbeddingsRequest, ImageGenerationRequest],
):
    provider, model = get_provider_model(request.provider, request.model)
    request.model = model
    request.provider = provider
    if request.model is None or request.provider is None:
        raise HTTPException(status_code=400, detail="Invalid model or provider")
    return request


@v1_router.post("/completions")
def completions(
    db: DatabaseSession, request: CompletionsRequest = Depends(convert_request), auth: AuthToken = Depends(get_auth)
):
    logger.info(f"Received completions request: {request.model_dump()}")

    try:
        assert request.provider is not None
        llm = get_llm_ai(request.provider)
    except NotImplementedError:
        raise HTTPException(status_code=400, detail="Provider not supported") from None

    ## remove tools from the model as it is not supported by the completions API
    model = request.model_dump(exclude={"provider", "response_format"})
    model.pop("tools", None)
    print("Calling completions", model)

    resp = llm.completions.create(**model)

    if request.stream:

        def add_usage_callback(response_text):
            logger.info("Stream done, adding usage to database")
            db.add_user_usage(
                auth.account_id, request.prompt, response_text, request.model, request.provider, "/completions"
            )

        run_id = thread_id = message_id = None
        return StreamingResponse(
            handle_stream(thread_id, run_id, message_id, resp, add_usage_callback), media_type="text/event-stream"
        )
    else:
        c = json.dumps(resp.model_dump())

        db.add_user_usage(auth.account_id, request.prompt, c, request.model, request.provider, "/completions")

        return JSONResponse(content=json.loads(c))


@v1_router.post("/get_agent_public_key")
def get_agent_public_key(agent_name: str = Query(...)):
    return get_public_key(derive_new_extended_private_key(get_hub_key(), agent_name))


@v1_router.post("/chat/completions")
def chat_completions(
    db: DatabaseSession,
    req: Request,
    request: ChatCompletionsRequest = Depends(convert_request),
    auth: AuthToken = Depends(get_auth),
):
    headers = dict(req.headers)
    run_id = headers.get("run_id")
    thread_id = headers.get("thread_id")
    message_id = headers.get("message_id")

    logger.info(f"Received chat completions request: {request.model_dump()}")

    try:
        assert request.provider is not None
        llm = get_llm_ai(request.provider)
    except NotImplementedError:
        raise HTTPException(status_code=400, detail="Provider not supported") from None

    print("/chat/completions", request.model_dump())
    try:
        resp = llm.chat.completions.create(**request.model_dump(exclude={"provider"}), timeout=DEFAULT_TIMEOUT)
    except Exception as e:
        error_message = str(e)
        if "Error code: 404" in error_message and "Model not found, inaccessible, and/or not deployed" in error_message:
            raise HTTPException(status_code=400, detail="Model not supported") from None
        else:
            raise HTTPException(status_code=400, detail=error_message) from None

    try:
        runner_data = json.loads(auth.runner_data or "{}")
        agent = runner_data.get("agent", None)
        runner_api_key = runner_data.get("runner_api_key", None)
        # TODO add signature generation for streams too
        if not request.stream and agent and is_trusted_runner_api_key(runner_api_key):
            print(f"Generation signature for {agent}...")

            request_model = f"{request.provider}::{request.model}" if request.provider else request.model

            response_message_text = resp.choices[0].message.content

            messages_dict: List[dict[str, str]] = [message.model_dump() for message in request.messages]

            signed_completion = get_signed_completion(
                agent_name=agent,
                response_message_text=response_message_text,
                model=request_model,
                messages=messages_dict,
                temperature=float(request.temperature),
                max_tokens=int(request.max_tokens or 0),
            )

            resp = resp.model_copy(update={"system_fingerprint": json.dumps(signed_completion)})

    except Exception as e:
        print(f"Signature generation failed: {e}")

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

        return StreamingResponse(
            handle_stream(thread_id, run_id, message_id, resp, add_usage_callback), media_type="text/event-stream"
        )

    else:
        c = json.dumps(resp.model_dump())
        try:
            db.add_user_usage(
                auth.account_id,
                json.dumps([x.model_dump() for x in request.messages]),
                c,
                request.model,
                request.provider,
                "/chat/completions",
            )
        except Exception as e:
            logger.error(f"Error adding usage to database: {e}")

        return JSONResponse(content=json.loads(c))


@mem_cache_with_timeout(300)
def get_models_inner():
    """Get all models from all providers.

    This function is cached.
    """
    logger.info("Refreshing models cache")
    all_models = []

    for p in Provider:
        try:
            client = get_llm_ai(p.value)
            provider_models = client.models.list()
            for model in provider_models.data:
                model_dict = model.model_dump()
                model_dict["id"] = f"{p.value}{PROVIDER_MODEL_SEP}{model_dict['id']}"
                all_models.append(model_dict)
            logger.info(f"Found {len(provider_models.data)} models from provider {p.value}")
        except Exception as e:
            logger.warn(f"Error getting models from provider {p.value}: {e}")

    logger.info(f"Found {len(all_models)} models")

    if not all_models:
        raise HTTPException(status_code=500, detail="No models found")

    return all_models


@v1_router.get("/models")
def get_models() -> JSONResponse:
    logger.debug("Getting models")
    all_models = get_models_inner()
    return JSONResponse(content={"object": "list", "data": all_models})


@v1_router.post("/embeddings")
def embeddings(
    db: DatabaseSession, request: EmbeddingsRequest = Depends(convert_request), auth: AuthToken = Depends(get_auth)
):
    logger.info(f"Received embeddings request: {request.model_dump()}")

    try:
        assert request.provider is not None
        llm = get_llm_ai(request.provider)
    except NotImplementedError:
        raise HTTPException(status_code=400, detail="Provider not supported") from None

    resp = llm.embeddings.create(**request.model_dump(exclude={"provider"}))

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
def revoke_nonce(db: DatabaseSession, nonce: RevokeNonce, auth: AuthToken = Depends(validate_signature)):
    """Revoke a nonce for the account."""
    logger.info(f"Received request to revoke nonce {nonce} for account {auth.account_id}")
    if auth.message != REVOKE_MESSAGE:
        raise HTTPException(status_code=401, detail="Invalid nonce revoke message")

    verify_revoke_nonce(auth)

    db.revoke_nonce(auth.account_id, nonce.nonce)
    return JSONResponse(content={"message": f"Nonce {nonce} revoked"})


@v1_router.post("/nonce/revoke/all")
def revoke_all_nonces(db: DatabaseSession, auth: AuthToken = Depends(validate_signature)):
    """Revoke all nonces for the account."""
    logger.info(f"Received request to revoke all nonces for account {auth.account_id}")
    if auth.message != REVOKE_ALL_MESSAGE:
        raise HTTPException(status_code=401, detail="Invalid nonce revoke message")

    verify_revoke_nonce(auth)

    db.revoke_all_nonces(auth.account_id)
    return JSONResponse(content={"message": "All nonces revoked"})


@v1_router.get("/nonce/list")
def list_nonces(db: DatabaseSession, auth: AuthToken = Depends(get_auth)):
    """List all nonces for the account."""
    nonces = db.get_account_nonces(auth.account_id)
    res = nonces.model_dump_json()
    logger.info(f"Listing nonces for account {auth.account_id}: {res}")
    return JSONResponse(content=json.loads(res))


def verify_revoke_nonce(auth):
    """If signature is too old, request will be rejected."""
    ts = int(auth.nonce)
    now = int(time.time() * 1000)
    if now - ts > 5 * 60 * 1000:
        raise HTTPException(status_code=401, detail="Invalid nonce")


@v1_router.get("/version")
def version() -> str:
    return importlib.metadata.version("nearai")


@v1_router.post("/images/generations")
def generate_images(
    db: DatabaseSession, request: ImageGenerationRequest = Depends(convert_request), auth: AuthToken = Depends(get_auth)
):
    logger.info(f"Received image generation request: {request.model_dump()}")

    try:
        assert request.provider is not None
        images_api = get_images_ai(request.provider)
    except NotImplementedError:
        raise HTTPException(status_code=400, detail="Provider not supported") from None

    try:
        resp = images_api.generate(**request.model_dump(exclude={"provider"}))
    except Exception as e:
        error_message = str(e)
        logger.error(f"Image generation failed: {error_message}")
        raise HTTPException(status_code=400, detail=f"Image generation failed: {error_message}") from None

    c = json.dumps(resp)
    logger.info(f"Image generation response: {c}")
    # TODO save image to s3 and save url in the DB
    image_url = "TODO"
    db.add_user_usage(
        auth.account_id, request.prompt, image_url, request.model or "default", request.provider, "/images/generations"
    )

    return JSONResponse(content=json.loads(c))
