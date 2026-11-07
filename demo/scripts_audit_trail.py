import json, httpx, sys
base = "http://127.0.0.1:8000"
ticket = {
    "subject": "Duplicate subscription charge",
    "body": "I was billed $149.00 twice for the same monthly subscription on the 5th. "
            "Only one charge should exist; please refund the duplicate to my card.",
    "customer_id": "CUS-DEMO-3005",
}
try:
    with httpx.Client(timeout=60) as c:
        r = c.post(base + "/tickets", json=ticket); r.raise_for_status()
        item = r.json(); print(json.dumps(item, indent=2))
        tid = item["id"]
        if item["status"] != "PENDING_FINANCE_APPROVAL":
            print(f"Expected PENDING_FINANCE_APPROVAL, got {item['status']}", file=sys.stderr); sys.exit(1)

        r = c.post(base + f"/tickets/{tid}/approval",
                   json={"decision": "approved", "reviewer_id": "finance.manager@example.com",
                         "reason": "Provider duplicate reference verified"})
        r.raise_for_status(); print(json.dumps(r.json(), indent=2))

        # Retrieve the persisted ticket and its full audit trail.
        r = c.get(base + f"/tickets/{tid}"); r.raise_for_status()
        t = r.json()
        print(json.dumps({
            "id": t["id"], "status": t["status"], "category": t["category"], "urgent": t["urgent"],
            "refund_amount": t["refund_amount"], "refund_id": t["refund_id"],
            "refund_status": t["refund_status"], "approval_decision": t["approval_decision"],
        }, indent=2))

        events = c.get(base + f"/tickets/{tid}/audit").json(); print(json.dumps(events, indent=2))
        types = [e["event"] for e in events]
        for expected in ("TICKET_RECEIVED", "CLOCKED_INJECTION", "PAYMENT_LOOKUP",
                         "FINANCE_APPROVAL_REQUIRED", "FINANCE_DECISION", "REFUND_PROVIDER_RESPONSE",
                         "TICKET_STATUS_UPDATED"):
            if expected not in types:
                print(f"Expected audit event {expected} missing", file=sys.stderr); sys.exit(1)
        print(f"OK: audit trail has {len(events)} events for ticket {tid}")
except httpx.HTTPStatusError as exc:
    print(f"Request failed: {exc.response.status_code} {exc.response.text}", file=sys.stderr); sys.exit(1)
except httpx.RequestError as exc:
    print(f"Could not reach the API at {base}: {exc}", file=sys.stderr)
    print("Start the server first:  uvicorn app.main:app", file=sys.stderr); sys.exit(1)
