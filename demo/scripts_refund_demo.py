import json, httpx
base = "http://127.0.0.1:8000"
ticket = {
    "subject": "Charged twice this month",
    "body": "Hi, I upgraded to the Pro plan on the 3rd and my card was charged twice, $49 each time. I can't find a way to get the second charge back in the billing page. Please help, this is my company card.",
    "customer_id": "CUS-DEMO-1025",
}
with httpx.Client(timeout=60) as c:
    r = c.post(base + "/tickets", json=ticket); r.raise_for_status()
    item = r.json(); print(json.dumps(item, indent=2))
    if item["status"] == "PENDING_FINANCE_APPROVAL":
        r = c.post(base + f"/tickets/{item['id']}/approval", json={"decision":"approved","reviewer_id":"finance.manager@example.com","reason":"Provider duplicate reference verified"})
        r.raise_for_status(); print(json.dumps(r.json(), indent=2))
    print(json.dumps(c.get(base + f"/tickets/{item['id']}/audit").json(), indent=2))
