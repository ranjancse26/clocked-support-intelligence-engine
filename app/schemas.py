from datetime import datetime
from pydantic import BaseModel, Field
from typing import Any

class TicketCreate(BaseModel):
    subject: str = Field(min_length=1, max_length=500)
    body: str = Field(min_length=1)
    customer_id: str = "CUS-DEMO"

class ApprovalRequest(BaseModel):
    decision: str = Field(pattern="^(approved|rejected|needs_information)$")
    reviewer_id: str = Field(min_length=1)
    reason: str | None = None

class StatsOut(BaseModel):
    tickets_processed: int = 0
    refunds_issued: float = 0.0
    quarantined: int = 0

class TicketOut(BaseModel):
    id: str
    subject: str
    body: str
    status: str
    category: str | None = None
    urgent: bool | None = None
    extracted: dict[str, Any] = {}
    clocked_results: dict[str, Any] = {}
    payment_evidence: dict[str, Any] = {}
    refund_amount: float | None = None
    refund_id: str | None = None
    refund_status: str | None = None
    approval_decision: str | None = None
    final_reply: str | None = None


class TicketListItem(BaseModel):
    id: str
    subject: str
    customer_id: str
    status: str
    category: str | None = None
    urgent: bool | None = None
    refund_amount: float | None = None
    created_at: datetime


class TicketsListOut(BaseModel):
    items: list[TicketListItem]
    total: int
