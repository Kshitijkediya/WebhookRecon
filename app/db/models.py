import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class EventState(str, PyEnum):
    RECEIVED = "received"
    PROCESSING = "processing"
    RECONCILED = "reconciled"
    FAILED = "failed"
    SKIPPED = "skipped"


class MismatchType(str, PyEnum):
    MISSED_EVENT = "missed_event"
    DUPLICATE_EVENT = "duplicate_event"
    STATE_MISMATCH = "state_mismatch"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(String(64), nullable=False)
    event_type = Column(String(128), nullable=False)
    payload = Column(JSON, nullable=False)
    idempotency_key = Column(String(256), unique=True, nullable=False, index=True)
    state = Column(Enum(EventState), default=EventState.RECEIVED, nullable=False, index=True)
    received_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)

    audit_logs = relationship("AuditLog", back_populates="event", lazy="selectin")


class LedgerRecord(Base):
    __tablename__ = "ledger_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id = Column(String(256), unique=True, nullable=False, index=True)
    status = Column(String(64), nullable=False)
    amount = Column(Numeric(precision=18, scale=2), nullable=True)
    currency = Column(String(3), nullable=True)
    provider = Column(String(64), nullable=True)
    raw_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("webhook_events.id"), nullable=True)
    mismatch_type = Column(Enum(MismatchType), nullable=True)
    action_taken = Column(String(256), nullable=False)
    details = Column(Text, nullable=True)
    resolved = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    event = relationship("WebhookEvent", back_populates="audit_logs")
