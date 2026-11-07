import json, httpx, sys
base = "http://127.0.0.1:8000"
ticket = {
    "subject": "Billed twice for the same plan renewal",
    "body": "I was charged $99.00 twice for the same annual plan renewal on the 12th. "
            "I only see a single charge in my billing page, and I need the duplicate reversed "
            "onto my company card as soon as possible.",
    "customer_id": "CUS-DEMO-3001",
}
try:
    with httpx.Client(timeout=60) as c:
        r = c.post(base + "/tickets", json=ticket); r.raise_for_status()
        item = r.json(); print(json.dumps(item, indent=2))
        if item["status"] != "PENDING_FINANCE_APPROVAL":
            print(f"Expected PENDING_FINANCE_APPROVAL, got {item['status']}", file=sys.stderr); sys.exit(1)
        r = c.post(base + f"/tickets/{item['id']}/approval",
                   json={"decision": "approved", "reviewer_id": "finance.manager@example.com",
                         "reason": "Provider duplicate reference DUP-778 verified; second charge confirmed"})
        r.raise_for_status(); print(json.dumps(r.json(), indent=2))
        if r.json()["status"] != "REFUND_SUCCEEDED":
            print(f"Expected REFUND_SUCCEEDED, got {r.json()['status']}", file=sys.stderr); sys.exit(1)
        print(json.dumps(c.get(base + f"/tickets/{item['id']}/audit").json(), indent=2))
except httpx.HTTPStatusError as exc:
    print(f"Request failed: {exc.response.status_code} {exc.response.text}", file=sys.stderr); sys.exit(1)
except httpx.RequestError as exc:
    print(f"Could not reach the API at {base}: {exc}", file=sys.stderr)
    print("Start the server first:  uvicorn app.main:app", file=sys.stderr); sys.exit(1)
