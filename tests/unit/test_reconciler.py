from app.services.reconciler import _states_match
from app.db.models import WebhookEvent, LedgerRecord, EventState


def make_event(event_type: str) -> WebhookEvent:
    e = WebhookEvent.__new__(WebhookEvent)
    e.event_type = event_type
    e.state = EventState.PROCESSING
    e.payload = {}
    return e


def make_ledger(status: str) -> LedgerRecord:
    r = LedgerRecord.__new__(LedgerRecord)
    r.status = status
    return r


def test_success_event_matches_paid_ledger():
    assert _states_match(make_event("payment.succeeded"), make_ledger("paid")) is True


def test_success_event_mismatches_pending_ledger():
    assert _states_match(make_event("payment.succeeded"), make_ledger("pending")) is False


def test_failed_event_matches_failed_ledger():
    assert _states_match(make_event("payment.failed"), make_ledger("failed")) is True


def test_unknown_event_type_is_not_a_mismatch():
    assert _states_match(make_event("some.other.event"), make_ledger("anything")) is True
