from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, Float, Boolean, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base

def now():
    return datetime.now(timezone.utc)

class Ticket(Base):
    __tablename__ = "tickets"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    subject: Mapped[str] = mapped_column(String(500))
    body: Mapped[str] = mapped_column(Text)
    customer_id: Mapped[str] = mapped_column(String(120), default="CUS-DEMO")
    status: Mapped[str] = mapped_column(String(80), default="RECEIVED")
    category: Mapped[str | None] = mapped_column(String(40), nullable=True)
    urgent: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    extracted: Mapped[dict] = mapped_column(JSON, default=dict)
    clocked_results: Mapped[dict] = mapped_column(JSON, default=dict)
    payment_evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    typellm_result: Mapped[dict] = mapped_column(JSON, default=dict)
    refund_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    refund_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    refund_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    approval_decision: Mapped[str | None] = mapped_column(String(40), nullable=True)
    final_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(100))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
