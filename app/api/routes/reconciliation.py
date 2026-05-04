import asyncio
import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.db.models import AuditLog, EventState, WebhookEvent
from app.db.session import AsyncSessionLocal
from app.worker.tasks import run_reconciliation

router = APIRouter()


@router.post("/trigger", status_code=202)
async def trigger_reconciliation() -> dict:
    task = run_reconciliation.delay()
    return {"status": "triggered", "task_id": task.id}


@router.get("/status")
async def reconciliation_status(db: AsyncSession = Depends(get_db)) -> dict:
    counts_result = await db.execute(
        select(WebhookEvent.state, func.count(WebhookEvent.id))
        .group_by(WebhookEvent.state)
    )
    state_counts = {state.value: count for state, count in counts_result.all()}

    unresolved_result = await db.execute(
        select(func.count(AuditLog.id)).where(AuditLog.resolved == False)  # noqa: E712
    )
    unresolved_count = unresolved_result.scalar_one()

    return {
        "event_states": {s.value: state_counts.get(s.value, 0) for s in EventState},
        "unresolved_mismatches": unresolved_count,
    }


@router.get("/stream")
async def stream_status() -> StreamingResponse:
    async def event_generator() -> AsyncGenerator[str, None]:
        while True:
            async with AsyncSessionLocal() as db:
                counts_result = await db.execute(
                    select(WebhookEvent.state, func.count(WebhookEvent.id))
                    .group_by(WebhookEvent.state)
                )
                state_counts = {state.value: count for state, count in counts_result.all()}

                unresolved_result = await db.execute(
                    select(func.count(AuditLog.id)).where(AuditLog.resolved == False)  # noqa: E712
                )
                unresolved_count = unresolved_result.scalar_one()

            data = {
                "event_states": {s.value: state_counts.get(s.value, 0) for s in EventState},
                "unresolved_mismatches": unresolved_count,
            }
            yield f"data: {json.dumps(data)}\n\n"
            await asyncio.sleep(5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/audit-logs")
async def list_audit_logs(
    resolved: bool | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    query = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    if resolved is not None:
        query = query.where(AuditLog.resolved == resolved)

    result = await db.execute(query)
    logs = result.scalars().all()

    return [
        {
            "id": str(log.id),
            "event_id": str(log.event_id) if log.event_id else None,
            "mismatch_type": log.mismatch_type,
            "action_taken": log.action_taken,
            "details": log.details,
            "resolved": log.resolved,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]
