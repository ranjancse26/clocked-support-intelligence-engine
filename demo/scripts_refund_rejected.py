import json, httpx, sys
base = "http://127.0.0.1:8000"
ticket = {
    "subject": "Duplicate monthly charge",
    "body": "My card was charged $49 twice this month after I upgraded to Pro. "
            "Please reverse the second charge.",
    "customer_id": "CUS-DEMO-3002",
}
try:
    with httpx.Client(timeout=60) as c:
        r = c.post(base + "/tickets", json=ticket); 
        r.raise_for_status()
        item = r.json(); 
        print(json.dumps(item, indent=2))

        if item["status"] != "PENDING_FINANCE_APPROVAL":
            print(f"Expected PENDING_FINANCE_APPROVAL, got {item['status']}", file=sys.stderr); sys.exit(1)
        r = c.post(base + f"/tickets/{item['id']}/approval",
                   json={"decision": "rejected", "reviewer_id": "finance.manager@example.com",
                         "reason": "Charges map to two distinct legitimate subscriptions; no duplicate found"})
        r.raise_for_status(); print(json.dumps(r.json(), indent=2))
        
        if r.json()["status"] != "REFUND_REJECTED":
            print(f"Expected REFUND_REJECTED, got {r.json()['status']}", file=sys.stderr); sys.exit(1)
        print(json.dumps(c.get(base + f"/tickets/{item['id']}/audit").json(), indent=2))
except httpx.HTTPStatusError as exc:
    print(f"Request failed: {exc.response.status_code} {exc.response.text}", file=sys.stderr); sys.exit(1)
except httpx.RequestError as exc:
    print(f"Could not reach the API at {base}: {exc}", file=sys.stderr)
    print("Start the server first:  uvicorn app.main:app", file=sys.stderr); sys.exit(1)
