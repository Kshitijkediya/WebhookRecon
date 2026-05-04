# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**WebhookRecon** is a Webhook Reconciliation Engine with Autonomous Ledger Healing. It ensures consistency between external webhook events and internal transaction records by automatically detecting mismatches and self-healing to maintain data integrity.

Core problem: webhook delivery failures, server crashes, or race conditions leave the internal ledger out of sync with external payment gateways (e.g., payment succeeds at Stripe but the internal record stays `PENDING`).

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI (async) |
| Database | PostgreSQL — ACID required for ledger integrity |
| ORM + Migrations | SQLAlchemy (async) + Alembic |
| Task Queue | Celery + Redis (broker + result backend) |
| Scheduled Jobs | Celery Beat — reconciliation runs every 15 min |
| Frontend | React 18 + TypeScript + Tailwind CSS (Vite) |
| Real-time | Server-Sent Events (SSE) — `GET /reconcile/stream` |
| Containers | Docker + docker-compose (app + celery_worker + celery_beat + postgres + redis) |
| CI/CD | GitHub Actions (`ci.yml` lint+test, `cd.yml` build+deploy) |
| Deployment | Render / Railway / fly.io |

## Project Structure

```
webhookrecon/
├── app/
│   ├── main.py                      # FastAPI app, CORS middleware, lifespan (creates tables)
│   ├── api/
│   │   ├── dependencies.py          # get_db() — async SQLAlchemy session
│   │   └── routes/
│   │       ├── webhooks.py          # POST /webhooks/receive (idempotent), GET /webhooks/{id}
│   │       └── reconciliation.py    # POST /reconcile/trigger, GET /reconcile/status,
│   │                                # GET /reconcile/stream (SSE), GET /reconcile/audit-logs
│   ├── core/
│   │   ├── config.py                # pydantic-settings — all config from env vars
│   │   └── security.py              # HMAC-SHA256 verify_signature() FastAPI dependency
│   ├── db/
│   │   ├── models.py                # WebhookEvent, LedgerRecord, AuditLog + enums
│   │   └── session.py               # async engine + AsyncSessionLocal
│   ├── services/
│   │   ├── reconciler.py            # find_mismatches() — diffs events vs ledger records
│   │   └── healer.py                # heal() — applies fixes per MismatchType
│   └── worker/
│       └── tasks.py                 # Celery app, process_webhook_event, run_reconciliation
├── frontend/
│   ├── src/
│   │   ├── App.tsx                  # Root dashboard — SSE for live stats, polls audit logs
│   │   ├── api.ts                   # All fetch calls + createStatusStream() (EventSource)
│   │   ├── types.ts                 # Shared TS types: StatusData, AuditLog, enums
│   │   └── components/
│   │       ├── StatCard.tsx         # Single stat tile
│   │       ├── AuditLogTable.tsx    # Audit log with resolved/open badges
│   │       └── ReconcileButton.tsx  # Trigger reconciliation with state feedback
│   ├── vite.config.ts               # Dev proxy: /webhooks + /reconcile → localhost:8000
│   └── tailwind.config.js
├── tests/
│   ├── conftest.py                  # pytest fixtures: async DB session, HTTPX test client
│   ├── unit/test_reconciler.py      # _states_match() unit tests
│   └── integration/test_webhooks.py # Webhook receive endpoint + signature verification
├── alembic/
│   ├── env.py                       # Async migration runner, reads DATABASE_URL from config
│   └── versions/                    # Migration files go here
├── .github/workflows/
│   ├── ci.yml                       # ruff + mypy + pytest (spins up postgres + redis services)
│   └── cd.yml                       # Docker build + push + Render deploy on merge to main
├── docker-compose.yml               # app + celery_worker + celery_beat + postgres + redis
├── Dockerfile
├── pyproject.toml                   # deps + ruff/mypy/pytest config
└── .env.example
```

## Core Domain Concepts

**Webhook Event States:** `received → processing → reconciled | failed | skipped`

**Reconciliation cycle (every 15 min via Celery Beat):**
1. `reconciler.find_mismatches()` queries events stuck in `PROCESSING` for >10 min and classifies them as `MISSED_EVENT`, `DUPLICATE_EVENT`, or `STATE_MISMATCH`
2. `healer.heal()` applies the fix: creates missing ledger record, skips duplicate, corrects ledger status, or flags unresolvable for manual review
3. Every action is written to `AuditLog` with `resolved=True/False`

**Signature verification:** `app/core/security.py::verify_signature()` is a FastAPI `Depends()` on `POST /webhooks/receive`. It computes HMAC-SHA256 over the raw request body and compares with `X-Webhook-Signature: sha256=<hex>`.

**Idempotency:** The webhook receiver checks for an existing `WebhookEvent` with the same `idempotency_key` (`{provider}:{event_id}`) before inserting.

## Development Commands

```bash
# Copy env template and start all services (app runs with --reload)
cp .env.example .env
docker-compose up -d

# First run: generate and apply the initial DB migration
alembic revision --autogenerate -m "initial"
alembic upgrade head

# Run tests (requires postgres + redis running)
pytest
pytest tests/unit/test_reconciler.py::test_success_event_matches_paid_ledger

# Lint and type check
ruff check .
mypy app/

# Frontend dev server (http://localhost:3000, proxies API to :8000)
cd frontend && npm install && npm run dev
```

## Environment Variables

All config is in `app/core/config.py` via pydantic-settings. Required vars:

| Variable | Example | Notes |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://...` | Must use `asyncpg` driver |
| `REDIS_URL` | `redis://localhost:6379/0` | |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/1` | |
| `WEBHOOK_SECRET` | any strong random string | Used for HMAC-SHA256 signature verification |
| `APP_ENV` | `development` | In `development`, CORS allows all origins |
| `CORS_ORIGINS` | `["https://yourapp.com"]` | Only used when `APP_ENV != development` |

## Key Architectural Decisions

- **PostgreSQL over MongoDB**: Ledger data requires ACID transactions. Reconciliation jobs do atomic writes that must roll back cleanly on failure.
- **Celery + Redis**: Reconciliation is a background task — the webhook receiver returns `202 Accepted` immediately and never blocks on business logic.
- **SSE over WebSockets**: Dashboard only needs server→client pushes for live stats; SSE is simpler and HTTP-native.
- **asyncio.run() in Celery tasks**: Worker uses `asyncio.run()` to call async DB functions rather than maintaining a separate sync SQLAlchemy engine.
- **Signature verification as Depends()**: Cannot be accidentally omitted on new routes; applied at the route decorator level.
- **CORS dev/prod split**: `APP_ENV=development` opens all origins for local DX; production requires explicit `CORS_ORIGINS` list.
