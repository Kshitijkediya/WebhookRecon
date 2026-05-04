import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.core.security import verify_signature
from app.db.models import EventState, WebhookEvent
from app.worker.tasks import process_webhook_event

router = APIRouter()


@router.post("/receive", dependencies=[Depends(verify_signature)], status_code=202)
async def receive_webhook(
    request: Request,
    provider: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    payload = await request.json()

    # Use provider-supplied event ID for idempotency; fall back to a new UUID
    event_id = payload.get("id") or payload.get("event_id") or str(uuid.uuid4())
    idempotency_key = f"{provider}:{event_id}"

    result = await db.execute(
        select(WebhookEvent).where(WebhookEvent.idempotency_key == idempotency_key)
    )
    if result.scalar_one_or_none():
        return {"status": "duplicate", "message": "Event already received"}

    event = WebhookEvent(
        provider=provider,
        event_type=payload.get("type", "unknown"),
        payload=payload,
        idempotency_key=idempotency_key,
        state=EventState.RECEIVED,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)

    process_webhook_event.delay(str(event.id))

    return {"status": "accepted", "event_id": str(event.id)}


@router.get("/{event_id}")
async def get_webhook_event(
    event_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(WebhookEvent).where(WebhookEvent.id == event_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return {
        "id": str(event.id),
        "provider": event.provider,
        "event_type": event.event_type,
        "state": event.state,
        "received_at": event.received_at.isoformat(),
        "processed_at": event.processed_at.isoformat() if event.processed_at else None,
        "retry_count": event.retry_count,
    }
