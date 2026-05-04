# WebhookRecon — Webhook Reconciliation Engine with Autonomous Ledger Healing

A backend system that ensures consistency between external webhook events and internal transaction records. It automatically detects mismatches and performs self-healing to maintain data integrity — built deployment-ready with a CI/CD pipeline.

---

## Problem Statement

In real-world systems, webhook delivery failures, server crashes, or race conditions can leave your internal state out of sync with external services.

**Example scenario:**
1. Payment gateway marks a transaction as `SUCCESS`
2. Webhook fires but your server is temporarily down
3. Gateway retries — but your server processes it twice, or never at all
4. Your ledger now shows `PENDING` while the gateway shows `PAID`

This system detects and autonomously fixes these inconsistencies.

---

## Core Features

| Feature | Description |
|---|---|
| **Webhook Listener** | REST endpoint that receives, validates, and queues incoming events |
| **Signature Verification** | HMAC-SHA256 verification on every incoming webhook (prevents spoofing) |
| **Transaction Ledger** | PostgreSQL-backed record of all transaction states |
| **Reconciliation Engine** | Periodic or on-demand diff between webhook events and ledger records |
| **Autonomous Healer** | Applies automatic fixes: replays missed events, reverses duplicates, or flags for review |
| **Audit Log** | Immutable log of every reconciliation action taken, with timestamps and outcomes |
| **Monitoring Dashboard** | React + Tailwind frontend showing live mismatch stats, event states, and audit trail |

---

## Webhook Event State Machine

```
received ──► processing ──► reconciled
                  │
                  ├──► failed (max retries exceeded)
                  └──► skipped (manual override)
```

Every event transitions through these states. The reconciliation engine acts on events stuck in `processing` or flagged as `failed`.

---

## Architecture

```
                    ┌─────────────────────────────────────────────┐
                    │              External Services               │
                    │     (Stripe / Razorpay / Payment Gateway)    │
                    └────────────────────┬────────────────────────┘
                                         │ Webhook POST
                                         ▼
                    ┌─────────────────────────────────────────────┐
                    │            FastAPI — Webhook Receiver        │
                    │   • HMAC-SHA256 signature verification       │
                    │   • Idempotency check (duplicate guard)      │
                    │   • Stores raw event → PostgreSQL            │
                    │   • Publishes task → Redis queue             │
                    └────────────┬────────────────────────────────┘
                                 │
                    ┌────────────▼────────────────────────────────┐
                    │            Celery Worker                     │
                    │   • Processes webhook event                  │
                    │   • Updates ledger record                    │
                    │   • Triggers reconciliation on anomaly       │
                    └────────────┬────────────────────────────────┘
                                 │
              ┌──────────────────▼──────────────────┐
              │                                     │
  ┌───────────▼──────────┐           ┌──────────────▼──────────┐
  │  Reconciliation      │           │   PostgreSQL             │
  │  Engine              │◄─────────►│   • webhook_events       │
  │  • Diffs events vs   │           │   • ledger_records       │
  │    ledger records    │           │   • audit_logs           │
  │  • Classifies        │           └─────────────────────────┘
  │    mismatches        │
  └───────────┬──────────┘
              │
  ┌───────────▼──────────┐
  │  Autonomous Healer   │
  │  • Replay missed     │
  │    events            │
  │  • Reverse duplicate │
  │    charges           │
  │  • Flag unresolvable │
  │    mismatches for    │
  │    manual review     │
  └───────────┬──────────┘
              │
  ┌───────────▼──────────┐
  │  React Dashboard     │
  │  • Live mismatch     │
  │    stats (SSE)       │
  │  • Event state view  │
  │  • Audit log viewer  │
  └──────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Reason |
|---|---|---|
| Backend | Python 3.11 + FastAPI | Async, fast, auto Swagger docs |
| Database | PostgreSQL (Supabase) | ACID transactions for ledger integrity |
| ORM + Migrations | SQLAlchemy (async) + Alembic | Type-safe queries, version-controlled schema |
| Task Queue | Celery + Redis | Background reconciliation, non-blocking webhook receipt |
| Frontend | React + Tailwind CSS | Live dashboard for monitoring |
| Real-time | Server-Sent Events (SSE) | Push mismatch updates to dashboard |
| Containers | Docker + docker-compose | Reproducible local dev (app + PG + Redis) |
| CI/CD | GitHub Actions | Lint + test on PR, deploy on merge to `main` |
| Hosting | Render / Railway / fly.io | Docker-native, free tiers available |

---

## Project Structure

```
webhookrecon/
├── app/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── webhooks.py          # POST /webhooks/receive
│   │   │   └── reconciliation.py    # GET /reconcile/status, POST /reconcile/trigger
│   │   └── dependencies.py          # Shared FastAPI deps (DB session, auth)
│   ├── core/
│   │   ├── config.py                # All config via pydantic-settings + env vars
│   │   └── security.py              # HMAC-SHA256 signature verification
│   ├── db/
│   │   ├── models.py                # WebhookEvent, LedgerRecord, AuditLog
│   │   └── session.py               # Async SQLAlchemy engine + session factory
│   ├── services/
│   │   ├── reconciler.py            # Diff logic: events vs ledger
│   │   └── healer.py                # Autonomous fix strategies
│   ├── worker/
│   │   └── tasks.py                 # Celery tasks: process_event, reconcile_batch
│   └── main.py                      # App init, router registration, lifespan hooks
├── frontend/                        # React + Tailwind dashboard
├── tests/
│   ├── unit/                        # Service-level tests (reconciler, healer)
│   └── integration/                 # Full flow tests against real DB + Redis
├── alembic/                         # DB migrations
├── .github/
│   └── workflows/
│       ├── ci.yml                   # Lint + typecheck + tests on every PR
│       └── cd.yml                   # Build Docker + deploy on merge to main
├── docker-compose.yml               # Local: app + postgres + redis
├── Dockerfile
├── .env.example                     # Template for required env vars
└── pyproject.toml
```

---

## CI/CD Pipeline

```
Push / PR ──► ci.yml
               ├── ruff (lint)
               ├── mypy (type check)
               └── pytest (unit + integration)

Merge to main ──► cd.yml
                   ├── Build Docker image
                   ├── Push to container registry
                   └── Deploy to hosting platform
```

---

## Environment Variables

```env
DATABASE_URL=postgresql+asyncpg://user:password@host/dbname
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
WEBHOOK_SECRET=your_hmac_secret_here
```

All secrets are injected via environment variables. A `.env.example` is committed; `.env` is gitignored.

---

## Use Cases

- **Payment systems** — Stripe/Razorpay webhook reconciliation against order records
- **Order tracking** — Ensure shipment status updates from logistics providers match internal state
- **Financial pipelines** — Detect and recover from partial transaction failures

---

## Future Enhancements

- ML-based anomaly detection (flag statistically unusual event patterns)
- Conflict resolution policies per event type (configurable: auto-fix vs. manual-review)
- Multi-provider support (pluggable signature verifiers per webhook source)
- Alerting integrations (Slack / email on unresolvable mismatches)
