import json, httpx, sys
base = "http://127.0.0.1:8000"
ticket = {
    "subject": "Duplicate $99 charge",
    "body": "I was charged $99.00 twice for the same transaction. Please refund the duplicate.",
    "customer_id": "CUS-DEMO-3004",
}
try:
    with httpx.Client(timeout=60) as c:
        r = c.post(base + "/tickets", json=ticket); r.raise_for_status()
        item = r.json(); print(json.dumps(item, indent=2))
        if item["status"] != "PENDING_FINANCE_APPROVAL":
            print(f"Expected PENDING_FINANCE_APPROVAL, got {item['status']}", file=sys.stderr); sys.exit(1)

        # First finance decision: approved -> refund executed.
        r = c.post(base + f"/tickets/{item['id']}/approval",
                   json={"decision": "approved", "reviewer_id": "finance.manager@example.com",
                         "reason": "Duplicate confirmed by provider"})
        r.raise_for_status(); print(json.dumps(r.json(), indent=2))

        # Second decision on the same ticket must conflict: it is no longer pending approval.
        r = c.post(base + f"/tickets/{item['id']}/approval",
                   json={"decision": "rejected", "reviewer_id": "finance.manager@example.com",
                         "reason": "Changed mind after refund already executed"})
        print(f"Second approval attempt -> HTTP {r.status_code}")
        print(json.dumps(r.json(), indent=2))
        if r.status_code != 409:
            print(f"Expected 409 conflict on duplicate approval, got {r.status_code}", file=sys.stderr); sys.exit(1)
        print("OK: duplicate finance decision correctly rejected with 409")
except httpx.HTTPStatusError as exc:
    print(f"Request failed: {exc.response.status_code} {exc.response.text}", file=sys.stderr)
    if exc.response.status_code != 409:
        sys.exit(1)
except httpx.RequestError as exc:
    print(f"Could not reach the API at {base}: {exc}", file=sys.stderr)
    print("Start the server first:  uvicorn app.main:app", file=sys.stderr); sys.exit(1)
