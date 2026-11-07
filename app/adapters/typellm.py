from app.config import settings

def questions():
    return {
        "category": {"type": "string", "enum": ["billing", "technical", "account", "other"], "instructions": "Classify the primary support issue.", "return_probabilities": True},
        "urgent": {"type": "boolean", "instructions": "Does this need priority handling? Urgency does not authorize a refund."},
        "handling_advice": {"type": "string", "depends_on": ["category", "urgent"], "instructions": "Give one internal next step. Verify payment records before refund decisions."},
        "duplicate_confirmed": {"type": "boolean", "source": "user", "when": {"category": "billing"}, "instructions": "Trusted billing integration result. True only when provider evidence confirms a duplicate."},
        "refund_amount": {"type": "number", "source": "user", "when": {"category": "billing", "duplicate_confirmed": True}, "instructions": "Application-calculated refund amount; do not infer it from the customer message."},
        "reply": {"type": "string", "depends_on": ["category", "urgent"], "instructions": "One concise customer reply. Do not claim refund approval or completion without evidence."},
    }

class TypeLLMAdapter:
    def __init__(self):
        self.client = None
        if not settings.mock_mode:
            if not settings.typellm_api_key:
                raise RuntimeError("TYPELLM_API_KEY required")
            from typellm import TypeLLMClient
            self.client = TypeLLMClient(api_key=settings.typellm_api_key)

    def generate(self, context):
        if self.client:
            return self.client.generate(context=context, questions=questions())
        billing = any(w in context.lower() for w in ("charged", "payment", "refund"))
        return {"status": "needs_input" if billing else "completed", "result": {"category": "billing" if billing else "other", "urgent": billing and "company card" in context.lower(), "handling_advice": "Verify provider transactions before refund consideration.", "reply": "I'm sorry about the billing issue; our team is checking the payment records."}, "needs_input": ["duplicate_confirmed"] if billing else [], "skipped": [], "resume_state": "mock"}

    def resume(self, response, answers):
        if self.client:
            return self.client.resume(response, answers)
        r = dict(response.get("result", {})); 
        r.update(answers)
        waiting = bool(r.get("duplicate_confirmed")) and "refund_approved" not in r
        return {"status": "needs_input" if waiting else "completed", "result": r, "needs_input": ["refund_approved"] if waiting else [], "skipped": [], "resume_state": "mock"}
