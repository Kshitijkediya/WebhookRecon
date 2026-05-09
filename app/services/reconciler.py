from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EventState, LedgerRecord, MismatchType, WebhookEvent


@dataclass
class Mismatch:
    event: WebhookEvent
    ledger_record: LedgerRecord | None
    mismatch_type: MismatchType
    details: str


async def find_mismatches(db: AsyncSession) -> list[Mismatch]:
    mismatches: list[Mismatch] = []

    stale_cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
    stale_result = await db.execute(
        select(WebhookEvent).where(
            WebhookEvent.state == EventState.PROCESSING,
            WebhookEvent.received_at < stale_cutoff,
        )
    )
    stale_events = stale_result.scalars().all()

    for event in stale_events:
        transaction_id = _extract_transaction_id(event)
        if not transaction_id:
            continue

        ledger_result = await db.execute(
            select(LedgerRecord).where(LedgerRecord.transaction_id == transaction_id)
        )
        ledger = ledger_result.scalar_one_or_none()

        if not ledger:
            mismatches.append(
                Mismatch(
                    event=event,
                    ledger_record=None,
                    mismatch_type=MismatchType.MISSED_EVENT,
                    details=f"No ledger record found for transaction {transaction_id}",
                )
            )
        elif not _states_match(event, ledger):
            mismatches.append(
                Mismatch(
                    event=event,
                    ledger_record=ledger,
                    mismatch_type=MismatchType.STATE_MISMATCH,
                    details=(
                        f"Event state implies '{event.event_type}' "
                        f"but ledger shows '{ledger.status}'"
                    ),
                )
            )

    # Duplicate events: same transaction_id received more than once
    received_result = await db.execute(
        select(WebhookEvent).where(WebhookEvent.state == EventState.RECEIVED)
    )
    received_events = received_result.scalars().all()

    seen_keys: dict[str, WebhookEvent] = {}
    for event in received_events:
        tx_id = _extract_transaction_id(event)
        if not tx_id:
            continue
        if tx_id in seen_keys:
            mismatches.append(
                Mismatch(
                    event=event,
                    ledger_record=None,
                    mismatch_type=MismatchType.DUPLICATE_EVENT,
                    details=f"Duplicate event for transaction {tx_id}",
                )
            )
        else:
            seen_keys[tx_id] = event

    return mismatches


def _extract_transaction_id(event: WebhookEvent) -> str | None:
    payload = event.payload or {}
    return (
        payload.get("transaction_id")
        or payload.get("order_id")
        or payload.get("id")
    )


def _states_match(event: WebhookEvent, ledger: LedgerRecord) -> bool:
    event_type_lower = event.event_type.lower()
    ledger_status_lower = ledger.status.lower()

    success_signals = {"payment.succeeded", "payment_intent.succeeded", "charge.captured"}
    failure_signals = {"payment.failed", "payment_intent.payment_failed", "charge.failed"}

    if event_type_lower in success_signals:
        return ledger_status_lower in {"success", "paid", "completed"}
    if event_type_lower in failure_signals:
        return ledger_status_lower in {"failed", "declined"}
    return True
