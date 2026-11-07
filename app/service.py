import json

from app.audit import audit
from app.handlers.billing_ticket_handler import BillingTicketHandler
from app.handlers.default_ticket_handler import DefaultTicketHandler
from app.handlers.base import (
    BaseTicketHandler,
    plain,
    clocked,
    typellm
)
from app.handlers.registry import HandlerRegistry

_registry = HandlerRegistry()
_registry.register(DefaultTicketHandler())
_registry.register(BillingTicketHandler())
registry = _registry

def register_handler(handler: BaseTicketHandler) -> None:
    """Convenience wrapper around :data:`registry.register`."""
    registry.register(handler)

def process_ticket(db, ticket, registry: HandlerRegistry | None = None):
    use_registry = _registry if registry is None else registry
    raw = f"Subject: {ticket.subject}\n\n{ticket.body}"
    audit(db, ticket.id, "TICKET_RECEIVED", {"subject": ticket.subject})

    guard = clocked.injection(raw)
    ticket.clocked_results = {"injection": guard}
    audit(db, ticket.id, "CLOCKED_INJECTION", guard)

    verdict = str(guard.get("verdict", "")).lower()
    score = float(guard.get("injection") or 0)
    threshold = float(guard.get("threshold", 0.5))

    if verdict in {"suspicious", "malicious", "blocked"} or score >= threshold:
        ticket.status = "QUARANTINED"; 
        db.commit()
        audit(db, ticket.id, "TICKET_QUARANTINED", {"reason": "Injection inspection"})
        return ticket

    pii = clocked.pii(raw)
    safe_text = pii.get("anonymized_text") or raw
    extracted = clocked.extract(safe_text)
    decision = clocked.decide(safe_text)

    ticket.extracted = extracted.get("fields", extracted)
    ticket.clocked_results = {"injection": guard, "pii": pii, "extract": extracted, "decide": decision}
    audit(db, ticket.id, "CLOCKED_ANALYSIS", {"extract": ticket.extracted, "decide": decision})

    context = safe_text + "\n\nClocked extraction: " + json.dumps(ticket.extracted, default=str) + "\nClocked decision: " + json.dumps(decision, default=str)
    response = typellm.generate(context)
    r = plain(response)

    ticket.typellm_result = r
    result = r.get("result", {})
    category = result.get("category")

    # Live SDK returns category as {value, probabilities, confidence}; persist only
    # the string value to the String(40) category column.
    ticket.category = category.get("value") if isinstance(category, dict) else category
    ticket.urgent = bool(result.get("urgent")) if result.get("urgent") is not None else None
    audit(db, ticket.id, "TYPELLM_INITIAL", {"status": r.get("status"), "result": result})

    handler = use_registry.get(ticket.category)
    handler.process(db, ticket, context, result, response)
    return ticket

def approve_ticket(db, ticket, reviewer_id: str, decision: str, reason: str | None):
    """Generic approval entry point for any ticket category.

    Routes to the approval logic of the handler owning ``ticket.category``.
    """
    handler = _registry.get(ticket.category)
    return handler.approve(db, ticket, reviewer_id, decision, reason)

def approve_refund(db, ticket, reviewer_id: str, decision: str, reason: str | None):
    """Backward-compatible alias for :func:`approve_ticket`.

    Kept so existing callers (and routes) continue to work unchanged.
    """
    return approve_ticket(db, ticket, reviewer_id, decision, reason)
