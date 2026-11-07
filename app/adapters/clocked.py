from app.config import settings

class ClockedAdapter:
    def __init__(self):
        self.client = None
        if not settings.mock_mode:
            if not settings.clocked_api_key:
                raise RuntimeError("CLOCKED_API_KEY required")
            from clocked_sdk import Clocked
            self.client = Clocked(api_key=settings.clocked_api_key, base_url=settings.clocked_base_url)

    def injection(self, text):
        if not self.client:
            bad = any(x in text.lower() for x in ("ignore all previous instructions", "bypass the refund policy", "reveal your system prompt"))
            return {"verdict": "suspicious" if bad else "clear", "injection": bad, "mock": True}
        return dict(self.client.injection(text=text, source="user", evidence=True))

    def pii(self, text):
        if not self.client:
            return {"anonymized_text": text, "mock": True, "note": "No real PII detection in mock mode"}
        return dict(self.client.pii(text=text, entities=["person", "email", "phone", "address", "credit_card", "username"], threshold=0.5, anonymize="replace"))

    def extract(self, text):
        if not self.client:
            return self._extract_mock(text)

        # Live SDK path: ask Clocked to extract structured fields from the free
        # text.  The field list is category-agnostic so it works for billing,
        # technical, account and other tickets alike.  Callers only need to
        # update the field description list when a new ticket domain is
        # supported.
        return dict(self.client.extract(text=text, fields={
            "issue_summary": {"description": "Concise customer issue summary"},
            "category_hint": {"description": "Most likely support category: billing, technical, account or other"},
            "urgency_hint": {"description": "Whether the issue needs priority handling"},
            "request_type": {"description": "Type of request: refund, inquiry, report, feature_request or other"},
            "amounts": {"description": "Any dollar amounts mentioned, as numbers"},
            "payment_method_type": {"description": "Payment method mentioned, if any"},
            "entities": {"description": "People, products, plans or accounts mentioned"},
        }))

    @staticmethod
    def _mock_issue_summary(text, low, is_billing_issue, is_technical_issue, is_account_issue, refund_requested, urgent):
        """Build a neutral issue summary from generic signals."""
        if not (is_billing_issue or is_technical_issue or is_account_issue or refund_requested or urgent):
            return None

        segments = []
        if refund_requested:
            segments.append("refund requested")
        if is_billing_issue:
            segments.append("billing/payment issue described")
        if is_technical_issue:
            segments.append("technical issue described")
        if is_account_issue:
            segments.append("account issue described")
        if urgent:
            segments.append("marked urgent")

        if not segments:
            return None

        return " ".join(segments).replace("  ", " ").capitalize()

    @staticmethod
    def _extract_mock(text):
        """Mock-mode fallback for :meth:`extract`.

        Returns a deterministic, JSON-serializable dict that keeps the same
        public contract as the live SDK response (``{"fields": ..., "mock": True}``)
        but is category-agnostic so it works for billing, technical, account and
        other tickets alike.

        Unknown values are ``None`` so producers don't accidentally treat an
        unextractable field as a validation failure.
        """
        import re

        low = text.lower()

        # --- Detect exact dollar amounts: "$49.00", "$1,200", "$49", "$99.50" ---
        amounts = re.findall(r"\$?\s*([\d,]+(?:\.\d{1,2})?)", text)
        amounts = [float(a.replace(",", "")) for a in amounts if a.replace(",", "")]

        # --- Category signals ---
        mentions_money = any(x in low for x in ("$", "charged", "charge", "billing", "bill", "refund", "price", "cost", "pay", "payment", "invoice", "subscription"))
        mentions_technical = any(x in low for x in ("error", "bug", "crash", "not working", "broken", "login", "password", "reset", "api", "sync", "slow", "down", "outage"))
        mentions_account = any(x in low for x in ("account", "profile", "email", "username", "billing address", "shipping address", "change my", "update my", "delete my", "close my"))

        is_billing_issue = mentions_money
        is_technical_issue = mentions_technical
        is_account_issue = mentions_account

        # --- Refund / money-back claims ---
        refund_requested = any(w in low for w in (
            "refund", "money back", "reverse the charge", "reverse the charges",
            "get the charge back", "get the charges back", "pay back", "repay"
        ))

        # --- Urgency signals ---
        urgent = any(w in low for w in ("urgent", "asap", "immediately", "right away", "emergency", "critical", "now"))

        # --- Request type ---
        request_type = None
        if refund_requested:
            request_type = "refund"
        elif any(w in low for w in ("how do i", "how to", "what is", "where is", "can you", "question", "inquiry")):
            request_type = "inquiry"
        elif any(w in low for w in ("report", "issue", "problem", "bug", "error", "complaint")):
            request_type = "report"
        elif any(w in low for w in ("feature", "request", "add", "new feature", "suggest")):
            request_type = "feature_request"
        elif is_billing_issue or is_technical_issue or is_account_issue:
            request_type = "other"

        # --- Category hint ---
        category_hint = None
        if is_billing_issue and not (is_technical_issue or is_account_issue):
            category_hint = "billing"
        elif is_technical_issue and not is_billing_issue:
            category_hint = "technical"
        elif is_account_issue and not (is_billing_issue or is_technical_issue):
            category_hint = "account"
        elif is_billing_issue or is_technical_issue or is_account_issue:
            category_hint = "other"

        # --- Payment method type (generic) ---
        payment_methods = {
            "credit card", "debit card", "company card", "business card",
            "bank account", "cash", "wire transfer", "paypal", "venmo",
            "apple pay", "google pay", "crypto", "bitcoin", "card",
        }
        payment_method_type = None
        for method in payment_methods:
            if re.search(r"\b" + re.escape(method) + r"\b", low):
                payment_method_type = method
                break

        # --- Currency label (deterministic) ---
        currency = "usd" if "$" in text or "usd" in low else None

        # --- Entities (simple token-level mention of capitalized words / plans) ---
        plans = {
            "pro", "premium", "enterprise", "professional", "family", "student",
            "basic", "standard", "business", "lifetime", "annual", "monthly", "trial",
        }
        entities = []
        for plan in plans:
            if f" {plan} " in f" {low} " or low.startswith(plan + " ") or low.endswith(f" {plan}"):
                entities.append(plan)
        for method in payment_methods:
            if payment_method_type == method and method not in entities:
                entities.append(method)

        fields = {
            "issue_summary": None,
            "category_hint": category_hint,
            "urgency_hint": urgent,
            "request_type": request_type,
            "amounts": amounts or None,
            "refund_requested": refund_requested,
            "payment_method_type": payment_method_type,
            "is_billing_issue": is_billing_issue,
            "is_technical_issue": is_technical_issue,
            "is_account_issue": is_account_issue,
            "currency": currency,
            "entities": entities or None,
        }

        # Override with a descriptive summary only if the ticket declares something actionable
        issue_summary = ClockedAdapter._mock_issue_summary(
            text, low, is_billing_issue, is_technical_issue, is_account_issue,
            refund_requested, urgent,
        )
        if issue_summary is not None:
            fields["issue_summary"] = issue_summary

        return {"fields": fields, "mock": True}

    def decide(self, text):
        if not self.client:
            t = text.lower()
            return {"answers": {
                "is_billing_issue": any(w in t for w in ("charged", "billing", "payment", "refund", "invoice", "subscription")),
                "is_technical_issue": any(w in t for w in ("error", "bug", "crash", "not working", "broken", "login", "password", "reset", "api", "sync", "slow", "down", "outage")),
                "is_account_issue": any(w in t for w in ("account", "profile", "email", "username", "billing address", "shipping address", "change my", "update my", "delete my", "close my")),
                "refund_requested": "refund" in t or "money back" in t,
                "urgent": any(w in t for w in ("urgent", "asap", "immediately", "right away", "emergency", "critical")),
            }, "mock": True}
        return dict(self.client.decide(state=text, questions={
            "is_billing_issue": {"type": "noul", "instructions": "Does this describe a billing/payment issue?"},
            "is_technical_issue": {"type": "noul", "instructions": "Does this describe a technical issue?"},
            "is_account_issue": {"type": "noul", "instructions": "Does this describe an account issue?"},
            "refund_requested": {"type": "noul", "instructions": "Does the customer request money back?"},
            "urgent": {"type": "noul", "instructions": "Does this need priority handling?"},
        }))

    def grounding(self, documents, question, answer):
        if not self.client:
            ok = "successfully processed" in answer.lower() and any("status: succeeded" in x["text"].lower() for x in documents)
            return {"verdict": "supported" if ok else "review_required", "answers_question": ok, "mock": True}
        return dict(self.client.grounding(documents=documents, question=question, answer=answer, evidence="all"))
