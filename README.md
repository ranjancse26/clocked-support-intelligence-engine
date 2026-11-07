# Clocked Support Intelligence Engine

## Overview

The Clocked Support Intelligence Engine is a Python/FastAPI reference project that combines Clocked APIs and TypeLLM for support-ticket triage and duplicate-charge resolution. It demonstrates how to classify incoming support tickets, route them to the right team, detect prompt injection attempts, and resolve duplicate-charge refund requests through a finance decision workflow.

These demo scripts are self-contained programs that exercise the Clocked Support Intelligence Engine API at `http://127.0.0.1:8000`. Each script:

1. Creates one support ticket through the API.
2. Drives that ticket through a specific workflow (triage, routing, quarantine, refund decision, audit trail, etc.).
3. Prints the JSON responses so you can see how the engine handles each case.

They are intended as runnable reference implementations that show the full ticket lifecycle - from submission through final disposition - along with persisted audit events for billing decisions.

## Product Screenshots

### Dashboard

![Dashboard](assets/Clocked%20Support%20Intelligence%20Web%20App%20-%20Dashboard.png)

### About

![About](assets/Clocked%20Support%20Intelligence%20Web%20App%20-%20About.png)

### Demo Scenarios

![Demo Scenarios](assets/Clocked%20Support%20Intelligence%20Web%20App%20-%20Demo%20Scenarios.png)

### Ticket Analysis 1

![Ticket Analysis 1](assets/Clocked%20Support%20Intelligence%20Web%20App%20-%20Ticket%20Analysis%201.png)

### Ticket Analysis 2

![Ticket Analysis 2](assets/Clocked%20Support%20Intelligence%20Web%20App%20-%20Ticket%20Analysis%202.png)

### Architecture Overview

![Architecture Overview](assets/Architecture-High-Level%20Overview.png)

![Workflow Diagram](assets/Clocked%20Support%20Intelligence%20Workflow%20Diagram.png)

## Features
- Clocked Injection inspection, PII, Extract, Decide and Verify
- TypeLLM typed category/urgency workflow
- Payment transaction lookup and duplicate evidence checks
- Finance approval endpoint
- Idempotency-keyed refund adapter contract
- SQLite ticket persistence and audit trail
- Mock mode for an end-to-end local demo

## Run locally

Python 3.10+:

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs and run:

Running the demos

Each demo script creates one ticket and drives it through a specific workflow. Run any of them from the repo root:

| Script | Scenario |
|--------|----------|
| `python demo\scripts_refund_approved.py` | Duplicate charge - refund approved |
| `python demo\scripts_refund_demo.py` | Full refund demo flow |
| `python demo\scripts_refund_rejected.py` | Finance decision - refund rejected |
| `python demo\scripts_refund_needs_information.py` | Finance decision - needs information |
| `python demo\scripts_prompt_injection_quarantined.py` | Prompt injection - ticket quarantined |
| `python demo\scripts_non_billing_routed.py` | Non-billing ticket routed to support |
| `python demo\scripts_audit_trail.py` | Audit trail end-to-end |
| `python demo\scripts_health_check.py` | Health check |
| `python demo\scripts_double_approval_conflict.py` | Double approval conflict |


Default `MOCK_MODE=true` uses simulated Clocked, TypeLLM and payment responses. The demo payment provider never moves real money.

## Live AI configuration

Set `MOCK_MODE=false`, `CLOCKED_API_KEY` and `TYPELLM_API_KEY`. Clocked calls use the documented `clocked-sdk` methods: `injection`, `pii`, `extract`, `decide`, `grounding`. TypeLLM uses `TypeLLMClient.generate()` and `client.resume()`.

The payment adapter intentionally remains a mock. Implement a provider-specific adapter (Stripe, Chargebee, Recurly, etc.) using the provider's current API, webhook verification, transaction references and idempotency contract before any real refund integration. Do not infer or invent provider API calls.

## Clocked and TypeLLM

Clocked and TypeLLM are the two external intelligence layers in this support ticket engine, each serving a distinct purpose in the shared pipeline (`app/service.py:process_ticket`).

### Clocked - the safety/security layer

`app/adapters/clocked.py:3` (`ClockedAdapter`) wraps the `clocked-sdk` with 5 methods, all running on untrusted customer input:

| Method | Role | Where it runs |
|--------|------|---------------|
| `injection` | Prompt-injection guard - scores/verdicts the raw ticket body; suspicious tickets are **QUARANTINED** before PII, extract, decide, or TypeLLM ever run | `service.py:262` |
| `pii` | Anonymizes PII in text used downstream | `service.py:275` |
| `extract` | Pulls structured fields (issue summary, category/urgency hint, amounts, payment method, entities) from free text | `service.py:277` |
| `decide` | Boolean answers (is_billing_issue, refund_requested, urgent, etc.) | `service.py:278` |
| `grounding` | Verifies the customer-facing refund reply against evidence documents before sending | `service.py:189` |

**Why it matters:** It establishes a trust boundary. Untrusted ticket content is scanned for injection, stripped of PII, and only then fed to the reasoning steps; the customer-facing reply is grounded against verified refund evidence so the engine never hallucinates a refund outcome to the customer.

### TypeLLM - the typed reasoning/workflow layer

`app/adapters/typellm.py:13` (`TypeLLMAdapter`) wraps `typellm` (`TypeLLMClient.generate()` / `.resume()`):

- `generate(context, questions())` - classifies `category` (billing/technical/account/other), `urgent`, `handling_advice`, `reply`, plus `duplicate_confirmed` and `refund_amount` declared as `source: "user"` fields resolved externally (`typellm.py:4-11`).
- `resume(response, answers)` - multi-turn resume; e.g. after the payment adapter confirms a duplicate, `duplicate_confirmed` is fed back so the workflow completes (`service.py:130`).

**Why it matters:** It produces reliable, typed classification rather than free-form LLM output, and it cleanly separates model-inferred fields from externally-verified facts. `duplicate_confirmed`/`refund_amount` come from the payment adapter (authoritative provider evidence), not the model - so refund decisions are never based solely on model output.

### How they fit together

The shared pipeline runs identically for every category (`service.py:259-300`):

1. Persist ticket - `TICKET_RECEIVED` audit
2. **Clocked injection** - quarantine if suspicious (`CLOCKED_INJECTION`)
3. **Clocked PII** - anonymized text
4. **Clocked extract + decide** - structured evidence (`CLOCKED_ANALYSIS`)
5. **TypeLLM generate** - category/urgency/advice (`TYPELLM_INITIAL`)
6. Category-specific handler runs (billing - payment lookup - `PENDING_FINANCE_APPROVAL`; others - `ROUTED_TO_SUPPORT`)
7. Finance approval - idempotent refund - **Clocked grounding** - customer reply - audit

Mock mode (`MOCK_MODE=true`) simulates both Clocked and TypeLLM deterministically, which is what `demo/scripts_audit_trail.py` exercises end-to-end against `http://127.0.0.1:8000`.

## API

- `POST /tickets` - create and process a support ticket
- `GET /tickets/{ticket_id}` - retrieve ticket
- `POST /tickets/{ticket_id}/approval` - finance decision (`approved`, `rejected`, `needs_information`)
- `GET /tickets/{ticket_id}/audit` - audit trail
- `GET /health` - health check

Example ticket:

```json
{
  "subject": "Charged twice this month",
  "body": "I upgraded to Pro and my card was charged twice, $49 each time.",
  "customer_id": "CUS-DEMO-1025"
}
```

## Workflow

1. Persist the incoming ticket and record a `TICKET_RECEIVED` audit event.
2. Clocked Injection inspects the untrusted content; suspicious tickets are quarantined and no further processing runs.
3. Clocked PII protects the text used downstream.
4. Clocked Extract and Decide produce structured evidence.
5. TypeLLM classifies category, urgency, and handling advice; external facts are declared as `source: user` fields and resolved through `generate()`/`resume()`.
6. A category-specific handler runs after classification. The shared pipeline (injection, PII, extract, decide, TypeLLM) is identical for every category; only the post-classification step is category-specific (for example, billing runs payment lookup/duplicate confirmation, while other categories route to support).
7. For billing tickets, the payment adapter retrieves authoritative transaction records and duplicate confirmation requires provider duplicate metadata/grouping; `source: user` fields represent payment facts, approval, and refund execution status.
8. Finance approval is recorded for confirmed duplicates (`approved`, `rejected`, or `needs_information`).
9. When approved, the payment adapter executes an idempotent refund keyed by the ticket.
10. Clocked Grounding checks the customer-facing refund claim.
11. Persist the outcome and audit events.

## Ticket scenarios

The engine handles tickets differently depending on their content, detected category, injection result, and payment evidence. Common scenarios:

### Duplicate charge - refund approved (billing)

The customer reports being charged twice and the payment provider confirms a provider-duplicate reference.

Request:

```json
{
  "subject": "Charged twice this month",
  "body": "Hi, I upgraded to the Pro plan on the 3rd and my card was charged twice, $49 each time. Please help, this is my company card.",
  "customer_id": "CUS-DEMO-1025"
}
```

Flow: injection clear - PII - Clocked extract/decide - TypeLLM classifies `billing` with `needs_input: [duplicate_confirmed]` - payment lookup confirms the duplicate group - ticket moves to `PENDING_FINANCE_APPROVAL` - finance posts `approved` - idempotent refund executed - Clocked grounding checks the customer-facing reply - `REFUND_SUCCEEDED`.

Expected status: `PENDING_FINANCE_APPROVAL` after creation; `REFUND_SUCCEEDED` after finance approval.

### Duplicate charge claimed but not confirmed (billing)

The customer claims a duplicate, but provider records show no provider-confirmed duplicate reference or no duplicate transaction group.

Flow: TypeLLM classifies `billing` - payment lookup `duplicate_confirmed: false` - `INVESTIGATING`; the billing team investigates and no refund is executed.

Expected status: `INVESTIGATING`.

### Finance decision - rejected or needs information

For a `PENDING_FINANCE_APPROVAL` ticket, a finance reviewer posts:

```json
{
  "decision": "rejected",
  "reviewer_id": "finance.manager@example.com",
  "reason": "Provider duplicate reference not verified"
}
```

- `approved` - idempotent refund is executed.
- `rejected` - `REFUND_REJECTED`, no refund is executed.
- `needs_information` - `NEEDS_INFORMATION`.

### Prompt injection - quarantined

The ticket body contains injection patterns (for example "ignore all previous instructions", "bypass the refund policy", "reveal your system prompt") or the injection score is at/above the threshold.

Flow: the injection guard quarantines the ticket before PII, extract, decide, or TypeLLM run.

Expected status: `QUARANTINED`.

### General / non-billing ticket

Category `technical`, `account`, or `other` (for example "How do I reset my password?").

Flow: TypeLLM returns `completed` with no `needs_input` - `ROUTED_TO_SUPPORT`.

Expected status: `ROUTED_TO_SUPPORT`.

### Ticket status reference

| Status | Meaning |
|---|---|
| `RECEIVED` | Ticket persisted, not yet processed. |
| `QUARANTINED` | Injection inspection flagged the ticket; processing stopped. |
| `ROUTED_TO_SUPPORT` | Non-billing ticket routed to the support team. |
| `INVESTIGATING` | Billing ticket: duplicate not confirmed by the provider. |
| `PENDING_FINANCE_APPROVAL` | Duplicate confirmed; awaiting a human finance decision. |
| `REFUND_REJECTED` | Finance rejected the refund. |
| `NEEDS_INFORMATION` | Finance needs more information before deciding. |
| `REFUND_SUCCEEDED` | Refund executed and the customer-facing reply passed grounding. |
| `REFUND_SUCCEEDED_REPLY_REVIEW` | Refund succeeded but the customer reply needs review before sending. |
| `REFUND_PENDING` | Refund initiated and still being processed. |
| `REFUND_FAILED` | Duplicate confirmed but the refund could not complete. |
| `PROCESSING_ERROR` | Ticket processing raised an exception. |

### Extending to new categories

Register a `BaseTicketHandler` subclass for a new category (for example `technical`, `account`, `feature_request`) and add it to the handler registry in `app/service.py`:

```python
from app.service import registry, BaseTicketHandler

class TechnicalTicketHandler(BaseTicketHandler):
    category = "technical"
    ...

registry.register(TechnicalTicketHandler())
```

The shared pipeline (injection, PII, extract, decide, TypeLLM) runs for every category; only the post-classification step is category-specific.

## Production hardening required

This is an end-to-end reference implementation, not a production-ready platform.

Before production:
- Replace the demo payment provider with a real provider-specific adapter.
- Add authentication, role-based access control, tenant isolation and reviewer identity verification.
- Use PostgreSQL and a durable queue; this starter processes synchronously and uses SQLite.
- Persist TypeLLM resume state using the SDK/API's supported serialization/reconstruction method. Do not pickle Python response objects or rely on in-memory objects across restarts.
- Add durable idempotency records and reconcile provider webhooks.
- Encrypt source documents and restrict access to raw PII.
- Add retries, dead-letter queues, rate limits, observability and operational alerts.
- Enforce refund limits and segregation of duties in deterministic policy code.
- Never authorize or execute refunds based solely on model output.

## Conclusion

The Clocked Support Intelligence Engine provides a complete, runnable reference for support-ticket triage and duplicate-charge resolution. It combines Clocked's safety layer (injection, PII, extract, decide, grounding) with TypeLLM's typed reasoning workflow, SQLite ticket persistence with audit trails, and an idempotent refund adapter contract. Before production use, replace the mock payment provider with a provider-specific adapter, add authentication and RBAC, migrate to PostgreSQL with a durable queue, and enforce refund policies in deterministic code rather than model output.
