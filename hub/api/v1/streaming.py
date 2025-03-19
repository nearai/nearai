import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import StreamingResponse
from hub.api.v1.auth import AuthToken, revokable_auth
from hub.api.v1.models import Delta, Message, get_session
from hub.api.v1.thread_routes import run_queues  # Import run_queues from thread_routes

streaming_router = APIRouter(prefix="/v1", tags=["streaming"])
logger = logging.getLogger(__name__)

