import json, httpx, sys
base = "http://127.0.0.1:8000"
ticket = {
    "subject": "Password reset",
    "body": "Hi, I can't log in to my account. How do I reset my password? I no longer have access to the recovery email on file.",
    "customer_id": "CUS-DEMO-2001",
}
try:
    with httpx.Client(timeout=60) as c:
        r = c.post(base + "/tickets", json=ticket); r.raise_for_status()
        item = r.json(); print(json.dumps(item, indent=2))
        if item["status"] != "ROUTED_TO_SUPPORT":
            print(f"Expected ROUTED_TO_SUPPORT, got {item['status']}", file=sys.stderr); sys.exit(1)
        print(json.dumps(c.get(base + f"/tickets/{item['id']}/audit").json(), indent=2))
except httpx.HTTPStatusError as exc:
    print(f"Request failed: {exc.response.status_code} {exc.response.text}", file=sys.stderr); sys.exit(1)
except httpx.RequestError as exc:
    print(f"Could not reach the API at {base}: {exc}", file=sys.stderr)
    print("Start the server first:  uvicorn app.main:app", file=sys.stderr); sys.exit(1)
