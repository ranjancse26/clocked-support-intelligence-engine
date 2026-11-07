from app.audit import audit
from app.handlers.base import BaseTicketHandler


class DefaultTicketHandler(BaseTicketHandler):
    """Fallback handler for every category without a dedicated implementation."""

    category = "default"

    def process(self, db, ticket, context: str, result: dict, response: dict) -> None:
        ticket.status = "ROUTED_TO_SUPPORT"
        ticket.final_reply = result.get("reply")
        db.commit()
        audit(
            db,
            ticket.id,
            "TICKET_ROUTED",
            {"category": ticket.category, "urgent": ticket.urgent},
        )

    def approve(self, db, ticket, reviewer_id: str, decision: str, reason: str | None):
        ticket.approval_decision = decision
        audit(
            db,
            ticket.id,
            "TICKET_REVIEW",
            {"reviewer_id": reviewer_id, "decision": decision, "reason": reason},
        )
        ticket.status = "CLOSED" if decision == "approved" else "NEEDS_INFORMATION"
        db.commit()
        audit(db, ticket.id, "TICKET_STATUS_UPDATED", {"status": ticket.status})
        return ticket