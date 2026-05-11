from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLog, EventState, LedgerRecord, MismatchType
from app.services.reconciler import Mismatch

MAX_RETRY = 3


async def heal(mismatch: Mismatch, db: AsyncSession) -> None:
    match mismatch.mismatch_type:
        case MismatchType.MISSED_EVENT:
            await _handle_missed_event(mismatch, db)
        case MismatchType.DUPLICATE_EVENT:
            await _handle_duplicate_event(mismatch, db)
        case MismatchType.STATE_MISMATCH:
            await _handle_state_mismatch(mismatch, db)


async def _handle_missed_event(mismatch: Mismatch, db: AsyncSession) -> None:
    event = mismatch.event

    if event.retry_count >= MAX_RETRY:
        event.state = EventState.FAILED
        await _log(
            db,
            event_id=str(event.id),
            mismatch_type=MismatchType.MISSED_EVENT,
            action="marked_failed",
            details=f"Exceeded {MAX_RETRY} retries. Manual review required.",
            resolved=False,
        )
        return

    # In production this would replay the event through the payment provider API
    transaction_id = _extract_transaction_id(event)
    if transaction_id:
        ledger = LedgerRecord(
            transaction_id=transaction_id,
            status="reconciled_from_webhook",
            provider=event.provider,
            raw_data=event.payload,
        )
        db.add(ledger)

    event.retry_count += 1
    event.state = EventState.RECONCILED
    event.processed_at = datetime.now(timezone.utc)

    await _log(
        db,
        event_id=str(event.id),
        mismatch_type=MismatchType.MISSED_EVENT,
        action="ledger_record_created",
        details=f"Created missing ledger entry for transaction {transaction_id}",
        resolved=True,
    )


async def _handle_duplicate_event(mismatch: Mismatch, db: AsyncSession) -> None:
    event = mismatch.event
    event.state = EventState.SKIPPED
    event.processed_at = datetime.now(timezone.utc)

    await _log(
        db,
        event_id=str(event.id),
        mismatch_type=MismatchType.DUPLICATE_EVENT,
        action="event_skipped",
        details="Duplicate event detected and skipped",
        resolved=True,
    )


async def _handle_state_mismatch(mismatch: Mismatch, db: AsyncSession) -> None:
    event = mismatch.event
    ledger = mismatch.ledger_record

    if not ledger:
        return

    event_type_lower = event.event_type.lower()
    success_signals = {"payment.succeeded", "payment_intent.succeeded", "charge.captured"}
    failure_signals = {"payment.failed", "payment_intent.payment_failed", "charge.failed"}

    if event_type_lower in success_signals:
        ledger.status = "success"
        ledger.updated_at = datetime.now(timezone.utc)
        action = "ledger_status_set_to_success"
    elif event_type_lower in failure_signals:
        ledger.status = "failed"
        ledger.updated_at = datetime.now(timezone.utc)
        action = "ledger_status_set_to_failed"
    else:
        # Ambiguous — flag for manual review
        event.state = EventState.FAILED
        await _log(
            db,
            event_id=str(event.id),
            mismatch_type=MismatchType.STATE_MISMATCH,
            action="flagged_for_review",
            details=mismatch.details,
            resolved=False,
        )
        return

    event.state = EventState.RECONCILED
    event.processed_at = datetime.now(timezone.utc)

    await _log(
        db,
        event_id=str(event.id),
        mismatch_type=MismatchType.STATE_MISMATCH,
        action=action,
        details=mismatch.details,
        resolved=True,
    )


async def _log(
    db: AsyncSession,
    event_id: str,
    mismatch_type: MismatchType,
    action: str,
    details: str,
    resolved: bool,
) -> None:
    log = AuditLog(
        event_id=event_id,
        mismatch_type=mismatch_type,
        action_taken=action,
        details=details,
        resolved=resolved,
    )
    db.add(log)


def _extract_transaction_id(event) -> str | None:
    payload = event.payload or {}
    return (
        payload.get("transaction_id")
        or payload.get("order_id")
        or payload.get("id")
    )
