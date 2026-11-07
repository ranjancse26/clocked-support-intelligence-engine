from uuid import uuid4

class DemoPaymentProvider:
    """Fake payment system for local demo only; no real money is moved."""
    def lookup(self, customer_id):
        return {
            "customer_id": customer_id,
            "currency": "USD",
            "provider_duplicate_reference": True,
            "transactions": [
                {"transaction_id": "TXN-10001", "amount": 49.0, "currency": "USD", "status": "succeeded", "duplicate_group": "DUP-778"},
                {"transaction_id": "TXN-10002", "amount": 49.0, "currency": "USD", "status": "succeeded", "duplicate_group": "DUP-778"},
            ],
        }

    def refund(self, transaction_id, amount, idempotency_key):
        return {"refund_id": "REF-" + uuid4().hex[:10].upper(), "transaction_id": transaction_id, "amount": amount, "currency": "USD", "status": "succeeded", "idempotency_key": idempotency_key}

def verify_duplicate(payment):
    groups = {}
    for tx in payment.get("transactions", []):
        if tx.get("status") == "succeeded":
            groups.setdefault(tx.get("duplicate_group"), []).append(tx)
    matches = [v for k, v in groups.items() if k and len(v) >= 2]
    if not payment.get("provider_duplicate_reference") or not matches:
        return False, 0.0, None
    # Demo rule only: select the second member of the provider-confirmed duplicate group.
    tx = matches[0][1]
    return True, float(tx["amount"]), tx["transaction_id"]
