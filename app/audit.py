from app.models import AuditEvent

def audit(db, ticket_id, event, details=None):
    db.add(AuditEvent(ticket_id=ticket_id, event_type=event, details=details or {}))
    db.commit()
