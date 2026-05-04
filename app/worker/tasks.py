import asyncio
from datetime import datetime, timezone

from celery import Celery
from celery.schedules import crontab
from sqlalchemy import select

from app.core.config import settings

celery_app = Celery(
    "webhookrecon",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.beat_schedule = {
    "reconcile-every-15-minutes": {
        "task": "app.worker.tasks.run_reconciliation",
        "schedule": crontab(minute="*/15"),
    },
}
celery_app.conf.timezone = "UTC"


@celery_app.task(name="app.worker.tasks.process_webhook_event", bind=True, max_retries=3)
def process_webhook_event(self, event_id: str) -> dict:
    return asyncio.run(_process_event_async(event_id))


@celery_app.task(name="app.worker.tasks.run_reconciliation")
def run_reconciliation() -> dict:
    return asyncio.run(_run_reconciliation_async())


async def _process_event_async(event_id: str) -> dict:
    from app.db.models import EventState, WebhookEvent
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(WebhookEvent).where(WebhookEvent.id == event_id)
        )
        event = result.scalar_one_or_none()
        if not event:
            return {"status": "not_found", "event_id": event_id}

        event.state = EventState.PROCESSING
        await db.commit()

        try:
            # Placeholder: in production, call payment provider API to verify
            # and update LedgerRecord here before marking reconciled
            event.state = EventState.RECONCILED
            event.processed_at = datetime.now(timezone.utc)
            await db.commit()
            return {"status": "processed", "event_id": event_id}
        except Exception as exc:
            event.state = EventState.FAILED
            event.retry_count += 1
            await db.commit()
            raise exc


async def _run_reconciliation_async() -> dict:
    from app.db.session import AsyncSessionLocal
    from app.services.healer import heal
    from app.services.reconciler import find_mismatches

    async with AsyncSessionLocal() as db:
        mismatches = await find_mismatches(db)
        for mismatch in mismatches:
            await heal(mismatch, db)
        await db.commit()
        return {"status": "completed", "mismatches_found": len(mismatches)}
