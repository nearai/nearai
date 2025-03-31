import logging
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import StreamingResponse

from hub.api.v1.auth import AuthToken, revokable_auth
from hub.api.v1.models import Delta, Message, get_session
from hub.api.v1.thread_routes import run_queues  # Import run_queues from thread_routes

streaming_router = APIRouter(prefix="/v1", tags=["streaming"])
logger = logging.getLogger(__name__)


@streaming_router.post("/threads/{thread_id}/messages/{message_id}/deltas")
async def create_delta(
    thread_id: str,
    message_id: str,
    delta: Delta = Body(...),
    auth: AuthToken = Depends(revokable_auth),
) -> None:
    """Create a delta for a message in a thread and queue it for streaming if the run is active.

    Args:
        thread_id (str): The ID of the thread.
        message_id (str): The ID of the message to attach the delta to.
        delta (Delta): The delta object containing content or metadata updates.
        auth (AuthToken): Authentication token for access control.

    Raises:
        HTTPException: If the message or thread isn't found or access is denied.

    """
    with get_session() as session:
        # Fetch the message
        message = session.get(Message, message_id)
        if not message:
            logger.error(f"Message not found: {message_id}")
            raise HTTPException(status_code=404, detail="Message not found")

        # Basic thread access check (adjust based on your auth model)
        if message.thread_id != thread_id:
            logger.error(f"Message {message_id} does not belong to thread {thread_id}")
            raise HTTPException(status_code=400, detail="Message-thread mismatch")
        # Add more sophisticated auth checks if needed (e.g., account_id matching)

        # Persist the delta
        delta_obj = Delta(
            id=delta.id if delta.id else None,  # Let the model generate ID if not provided
            content=delta.content,
            filename=delta.filename,
            step_details=delta.step_details if hasattr(delta, "step_details") else None,
            meta_data=delta.meta_data if hasattr(delta, "meta_data") else None,
        )
        session.add(delta_obj)
        session.commit()
        logger.info(f"Created delta {delta_obj.id} for message {message_id}")

        # If the message's run is being streamed, queue the delta
        if message.run_id and message.run_id in run_queues:
            delta_event = delta_obj.to_openai().model_dump_json()  # Convert to OpenAI-compatible JSON
            await run_queues[message.run_id].put(delta_event)
            logger.debug(f"Queued delta {delta_obj.id} for run {message.run_id}")


@streaming_router.get("/threads/{thread_id}/subscribe")
async def thread_subscribe(
    thread_id: str,
    message_id: Optional[str] = None,
    auth: AuthToken = Depends(revokable_auth),
):
    """Subscribe to deltas for a thread (for testing or future use, primary streaming is handled via runs)."""
    with get_session() as session:
        # Basic thread existence check
        from hub.api.v1.models import Thread  # Import here to avoid circularity

        thread = session.get(Thread, thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")

        # Placeholder generator (replace with real logic if needed)
        async def placeholder_stream():
            yield 'data: {"message": "Streaming placeholder for thread ' + thread_id + '"}\n\n'

        return StreamingResponse(placeholder_stream(), media_type="text/event-stream")
