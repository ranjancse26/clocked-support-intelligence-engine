import json, httpx, sys
base = "http://127.0.0.1:8000"
try:
    with httpx.Client(timeout=30) as c:
        r = c.get(base + "/health")
        r.raise_for_status()
        print(json.dumps(r.json(), indent=2))
except httpx.HTTPStatusError as exc:
    print(f"Health check failed: {exc.response.status_code} {exc.response.text}", file=sys.stderr)
    sys.exit(1)
except httpx.RequestError as exc:
    print(f"Could not reach the API at {base}: {exc}", file=sys.stderr)
    print("Start the server first:  uvicorn app.main:app", file=sys.stderr)
    sys.exit(1)
