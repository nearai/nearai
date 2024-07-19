from typing import Iterable, List, Dict, Any
from pydantic import BaseModel
from typing import Optional, Union, List, Dict
from hub.api.v1.sql import SqlClient
from hub.api.v1.completions import get_llm_ai, Message, handle_stream, Provider
from hub.api.v1.auth import get_current_user, AuthToken

import logging
import json

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from fastapi.responses import StreamingResponse

v1_router = APIRouter()
db = SqlClient()
logger = logging.getLogger(__name__)
security = HTTPBearer()

PROVIDER_MODEL_SEP = "::"


def get_provider_model(provider: Optional[str], model: str):
    if PROVIDER_MODEL_SEP in model:
        return model.split(PROVIDER_MODEL_SEP)
    return provider, model


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
    provider: Optional[str] = None
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


class CompletionsRequest(LlmRequest):
    """Request for completions."""
    prompt: str


class ChatCompletionsRequest(LlmRequest):
    """Request for chat completions."""
    messages: List[Message]


class EmbeddingsRequest(BaseModel):
    """Request for embeddings."""
    input: str | List[str] | Iterable[int] | Iterable[Iterable[int]]
    model: Optional[str] = f"fireworks{PROVIDER_MODEL_SEP}nomic-ai/nomic-embed-text-v1.5"
    provider: Optional[str] = None


# The request might come as provider::model
# OpenAI API specs expects model name to be only the model name, not provider::model
def convert_request(request: ChatCompletionsRequest | CompletionsRequest | EmbeddingsRequest):
    provider, model = get_provider_model(request.provider, request.model)
    request.model = model
    request.provider = provider
    return request


@v1_router.post("/completions")
def completions(request: CompletionsRequest = Depends(convert_request), auth: AuthToken = Depends(get_current_user)):
    logger.info(f"Received completions request: {request.model_dump()}")

    try:
        llm = get_llm_ai(request.provider)
    except NotImplementedError:
        raise HTTPException(status_code=400, detail="Provider not supported")

    resp = llm.completions.create(
        **request.model_dump(exclude={"provider", "response_format"}))

    if request.stream:
        def add_usage_callback(response_text):
            logger.info(f"Stream done, adding usage to database")
            db.add_user_usage(auth.account_id, request.prompt, response_text,
                              request.model, request.provider, "/completions")

        return StreamingResponse(handle_stream(resp, add_usage_callback), media_type="text/event-stream")
    else:
        c = json.dumps(resp.model_dump())

        db.add_user_usage(
            auth.account_id, request.prompt, c, request.model, request.provider, "/completions")

        return JSONResponse(content=json.loads(c))


@v1_router.post("/chat/completions")
async def chat_completions(request: ChatCompletionsRequest = Depends(convert_request), auth: AuthToken = Depends(get_current_user)):
    logger.info(f"Received chat completions request: {request.model_dump()}")

    try:
        llm = get_llm_ai(request.provider)
    except NotImplementedError:
        raise HTTPException(status_code=400, detail="Provider not supported")

    resp = llm.chat.completions.create(
        **request.model_dump(exclude={"provider"}))

    if request.stream:
        def add_usage_callback(response_text):
            logger.info(f"Stream done, adding usage to database")
            db.add_user_usage(auth.account_id, json.dumps([x.model_dump() for x in request.messages]), response_text,
                              request.model, request.provider, "/chat/completions")

        return StreamingResponse(handle_stream(resp, add_usage_callback), media_type="text/event-stream")

    else:
        c = json.dumps(resp.model_dump())
        db.add_user_usage(
            auth.account_id, json.dumps([x.model_dump() for x in request.messages]), c, request.model, request.provider, "/chat/completions")

        return JSONResponse(content=json.loads(c))


@v1_router.get("/models")
async def get_models():
    all_models: List[Dict[str, Any]] = []

    for p in Provider:
        try:
            provider_models = get_llm_ai(p.value).models.list()
            for model in provider_models:
                model_dict = model.model_dump()
                model_dict['id'] = f"{p.value}{PROVIDER_MODEL_SEP}{model_dict['id']}"
                all_models.append(model_dict)
        except Exception as e:
            logger.error(f"Error getting models from provider {p.value}: {e}")

    # Format the response to match OpenAI API structure
    response = {
        "object": "list",
        "data": all_models
    }

    return JSONResponse(content=response)


@v1_router.post("/embeddings")
async def embeddings(request: EmbeddingsRequest = Depends(convert_request), auth: AuthToken = Depends(get_current_user)):
    logger.info(f"Received embeddings request: {request.model_dump()}")

    try:
        llm = get_llm_ai(request.provider)
    except NotImplementedError:
        raise HTTPException(status_code=400, detail="Provider not supported")

    resp = llm.embeddings.create(
        **request.model_dump(exclude={"provider"}))

    c = json.dumps(resp.model_dump())
    db.add_user_usage(
        auth.account_id, request.input, c, request.model, request.provider, "/embeddings")

    return JSONResponse(content=json.loads(c))
