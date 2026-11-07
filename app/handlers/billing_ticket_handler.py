from app.adapters.payment import verify_duplicate
from app.audit import audit
from app.config import settings
from app.handlers.base import BaseTicketHandler, clocked, payments, plain, typellm


class BillingTicketHandler(BaseTicketHandler):
    """Handles billing/payment tickets: duplicate verification, refund candidates, finance approval.

    This preserves the previous refund-centric behaviour behind the generic
    handler interface, so existing billing tickets continue to work unchanged.
    """

    category = "billing"

    def process(self, db, ticket, context: str, result: dict, response: dict) -> None:
        payment = payments.lookup(ticket.customer_id)
        duplicate, amount, duplicate_tx = verify_duplicate(payment)
        ticket.payment_evidence = {
            **payment,
            "duplicate_confirmed": duplicate,
            "refund_candidate": amount,
            "duplicate_transaction_id": duplicate_tx,
        }
        ticket.refund_amount = amount
        audit(db, ticket.id, "PAYMENT_LOOKUP", ticket.payment_evidence)

        if not duplicate:
            ticket.status = "INVESTIGATING"
            ticket.final_reply = (
                "I'm sorry about the unexpected charge; we could not confirm "
                "a duplicate payment, so our billing team will investigate."
            )
            db.commit()
            audit(db, ticket.id, "TICKET_STATUS_UPDATED", {"status": ticket.status})
            return

        if not settings.mock_mode:
            # TypeLLM only asks for duplicate_confirmed here; refund_amount is
            # conditional on duplicate_confirmed being true, so it must not be
            # sent in this resume call. It is already persisted on
            # ticket.refund_amount from verify_duplicate above.
            response = typellm.resume(response, {"duplicate_confirmed": duplicate})
            ticket.typellm_result = plain(response)

        ticket.status = "PENDING_FINANCE_APPROVAL"
        db.commit()
        audit(
            db,
            ticket.id,
            "FINANCE_APPROVAL_REQUIRED",
            {"amount": amount, "transaction_id": duplicate_tx},
        )

    def approve(self, db, ticket, reviewer_id: str, decision: str, reason: str | None):
        if ticket.status != "PENDING_FINANCE_APPROVAL":
            raise ValueError("Ticket is not pending finance approval")

        ticket.approval_decision = decision
        audit(
            db,
            ticket.id,
            "FINANCE_DECISION",
            {"reviewer_id": reviewer_id, "decision": decision, "reason": reason},
        )

        if decision != "approved":
            ticket.status = "REFUND_REJECTED" if decision == "rejected" else "NEEDS_INFORMATION"
            ticket.final_reply = "Our billing team is reviewing the payment details and will follow up."
            db.commit()
            audit(db, ticket.id, "TICKET_STATUS_UPDATED", {"status": ticket.status})
            return ticket

        evidence = ticket.payment_evidence
        if not evidence.get("duplicate_confirmed"):
            raise ValueError("Refund blocked: duplicate not verified")

        txid = evidence.get("duplicate_transaction_id")
        amount = float(ticket.refund_amount or 0)

        if not txid or amount <= 0:
            raise ValueError("Refund blocked: missing transaction or amount")

        refund = payments.refund(txid, amount, f"support-refund-{ticket.id}")
        ticket.refund_id = refund["refund_id"]
        ticket.refund_status = refund["status"]
        audit(db, ticket.id, "REFUND_PROVIDER_RESPONSE", refund)

        if refund["status"] == "succeeded":
            docs = [
                {
                    "id": "refund-record",
                    "text": (
                        f"Refund ID: {refund['refund_id']}\n"
                        f"Transaction ID: {txid}\n"
                        f"Amount: USD {amount:.2f}\n"
                        "Status: succeeded"
                    ),
                }
            ]
            reply = f"We verified the duplicate ${amount:.2f} charge and successfully processed a refund to your original payment method."
            check = clocked.grounding(docs, "Does the reply accurately describe the refund outcome?", reply)
            audit(db, ticket.id, "CLOCKED_GROUNDING", check)
            if check.get("answers_question") is False or check.get("verdict") in {
                "unsupported",
                "contradicted",
                "review_required",
            }:
                ticket.status = "REFUND_SUCCEEDED_REPLY_REVIEW"
                ticket.final_reply = None
            else:
                ticket.status = "REFUND_SUCCEEDED"
                ticket.final_reply = reply
        elif refund["status"] == "pending":
            ticket.status = "REFUND_PENDING"
            ticket.final_reply = (
                "We verified the duplicate charge and initiated a refund; "
                "it is currently being processed."
            )
        else:
            ticket.status = "REFUND_FAILED"
            ticket.final_reply = (
                "We confirmed the duplicate charge, but the refund could not "
                "be completed; our billing team will follow up."
            )

        db.commit()
        audit(db, ticket.id, "TICKET_STATUS_UPDATED", {"status": ticket.status})
        return ticket