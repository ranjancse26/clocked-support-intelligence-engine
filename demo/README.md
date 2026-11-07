# Demo scripts

## Overview

The Clocked Support Intelligence Engine is a Python/FastAPI reference project
that combines Clocked APIs and TypeLLM for support-ticket triage and
duplicate-charge resolution. It demonstrates how to classify incoming support
tickets, route them to the right team, detect prompt injection attempts, and
resolve duplicate-charge refund requests through a finance decision workflow.

These demo scripts are self-contained programs that exercise the Clocked Support
Intelligence Engine API at `http://127.0.0.1:8000`. Each script:

1. Creates one support ticket through the API.
2. Drives that ticket through a specific workflow (triage, routing,
   quarantine, refund decision, audit trail, etc.).
3. Prints the JSON responses so you can see how the engine handles each case.

They are intended as runnable reference implementations that show the full
ticket lifecycle — from submission through final disposition — along with
persisted audit events for billing decisions.

## Running the demos

Run any script from the repo root:

```powershell
.venv\Scripts\python.exe demo\scripts_refund_approved.py
```

## Prerequisites

1. Install dependencies: `pip install -r requirements.txt`
2. Start the API server from the repo root:

   ```powershell
   # Deterministic local demo (simulated Clocked / TypeLLM / payments):
   $env:MOCK_MODE="true"; .venv\Scripts\uvicorn.exe app.main:app

   # Live AI mode (requires CLOCKED_API_KEY / TYPELLM_API_KEY in .env):
   .venv\Scripts\uvicorn.exe app.main:app
   ```

3. Open http://127.0.0.1:8000/docs for the interactive API reference.

## Scripts

| Script | Use case | Expected terminal status |
|--------|----------|--------------------------|
| `scripts_health_check.py` | `GET /health` — verify the server is up and mock mode | `{"status": "ok", ...}` |
| `scripts_non_billing_routed.py` | Password-reset style ticket (category `other`) | `ROUTED_TO_SUPPORT` |
| `scripts_prompt_injection_quarantined.py` | Prompt injection attempt ("ignore all previous instructions ...") | `QUARANTINED` |
| `scripts_refund_approved.py` | Duplicate charge → finance approves → idempotent refund | `REFUND_SUCCEEDED` |
| `scripts_refund_rejected.py` | Duplicate charge → finance rejects | `REFUND_REJECTED` |
| `scripts_refund_needs_information.py` | Duplicate charge → finance requests more info | `NEEDS_INFORMATION` |
| `scripts_double_approval_conflict.py` | Second finance decision on an already-decided ticket | `409` conflict |
| `scripts_audit_trail.py` | Full billing lifecycle + persisted ticket + audit events | `REFUND_SUCCEEDED` + audit |

## Notes

- Default `MOCK_MODE=true` uses simulated Clocked, TypeLLM and payment responses; no real money moves and no external network calls are made. This is the recommended mode for these demos.
- With `MOCK_MODE=false`, the server calls live Clocked/TypeLLM APIs using `CLOCKED_API_KEY`/`TYPELLM_API_KEY` from `.env`; results depend on those providers.
- The refund idempotency key is derived from the ticket id (`support-refund-{ticket.id}`), so repeating a finance decision on the same ticket is a conflict (`409`), not a duplicate refund.
- This is a reference starter, not a production payment platform — see the production hardening section of `README.md` before integrating a real provider.
