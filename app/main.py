import uuid
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.db import Base, engine, get_db
from app.models import Ticket, AuditEvent
from app.schemas import TicketCreate, ApprovalRequest, TicketOut, StatsOut, TicketListItem, TicketsListOut
from app.service import process_ticket, approve_refund

Base.metadata.create_all(bind=engine)
app = FastAPI(title="Clocked Support Intelligence Engine", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def output(t):
    return TicketOut(id=t.id, subject=t.subject, body=t.body, status=t.status, category=t.category, urgent=t.urgent, extracted=t.extracted or {}, clocked_results=t.clocked_results or {}, payment_evidence=t.payment_evidence or {}, refund_amount=t.refund_amount, refund_id=t.refund_id, refund_status=t.refund_status, approval_decision=t.approval_decision, final_reply=t.final_reply)

@app.get("/health")
def health():
    from app.config import settings
    return {"status": "ok", "mock_mode": settings.mock_mode}


@app.get("/stats", response_model=StatsOut)
def stats(db: Session = Depends(get_db)):
    tickets_processed = db.query(func.count(Ticket.id)).scalar() or 0
    refunds_issued = (
        db.query(func.coalesce(func.sum(Ticket.refund_amount), 0.0))
        .filter(Ticket.status.in_(["REFUND_SUCCEEDED", "REFUND_SUCCEEDED_REPLY_REVIEW"]))
        .scalar()
        or 0.0
    )
    quarantined = (
        db.query(func.count(Ticket.id)).filter(Ticket.status == "QUARANTINED").scalar()
        or 0
    )
    return StatsOut(
        tickets_processed=int(tickets_processed),
        refunds_issued=float(refunds_issued),
        quarantined=int(quarantined),
    )

@app.post("/tickets", response_model=TicketOut)
def create_ticket(payload: TicketCreate, db: Session = Depends(get_db)):
    t = Ticket(id="SUP-" + uuid.uuid4().hex[:12].upper(), subject=payload.subject, body=payload.body, customer_id=payload.customer_id)
    db.add(t); db.commit(); db.refresh(t)
    try:
        process_ticket(db, t)
    except Exception as exc:
        t.status = "PROCESSING_ERROR"; db.commit()
        raise HTTPException(502, f"Processing failed: {exc}")
    db.refresh(t)
    return output(t)

@app.get("/tickets", response_model=TicketsListOut)
def list_tickets(
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
):
    query = db.query(Ticket).order_by(Ticket.created_at.desc())
    total = query.count()
    rows = query.offset(offset).limit(limit).all()
    return TicketsListOut(
        items=[
            TicketListItem(
                id=t.id,
                subject=t.subject,
                customer_id=t.customer_id,
                status=t.status,
                category=t.category,
                urgent=t.urgent,
                refund_amount=t.refund_amount,
                created_at=t.created_at,
            )
            for t in rows
        ],
        total=total,
    )

@app.get("/tickets/{ticket_id}", response_model=TicketOut)
def get_ticket(ticket_id: str, db: Session = Depends(get_db)):
    t = db.get(Ticket, ticket_id)
    if not t: raise HTTPException(404, "Ticket not found")
    return output(t)

@app.post("/tickets/{ticket_id}/approval", response_model=TicketOut)
def approval(ticket_id: str, payload: ApprovalRequest, db: Session = Depends(get_db)):
    t = db.get(Ticket, ticket_id)
    if not t: raise HTTPException(404, "Ticket not found")
    try:
        approve_refund(db, t, payload.reviewer_id, payload.decision, payload.reason)
    except ValueError as exc:
        raise HTTPException(409, str(exc))
    db.refresh(t)
    return output(t)

@app.get("/tickets/{ticket_id}/audit")
def audit_trail(ticket_id: str, db: Session = Depends(get_db)):
    if not db.get(Ticket, ticket_id): raise HTTPException(404, "Ticket not found")
    rows = db.query(AuditEvent).filter(AuditEvent.ticket_id == ticket_id).order_by(AuditEvent.id).all()
    return [{"event": x.event_type, "details": x.details, "created_at": x.created_at.isoformat()} for x in rows]


# Serve the frontend at the root. API routes above take precedence.
@app.get("/", include_in_schema=False)
def serve_frontend():
    return FileResponse("frontend/index.html")

@app.get("/style.css", include_in_schema=False)
def serve_css():
    return FileResponse("frontend/style.css")

@app.get("/script.js", include_in_schema=False)
def serve_js():
    return FileResponse("frontend/script.js")

app.mount("/static", StaticFiles(directory="frontend"), name="frontend")
