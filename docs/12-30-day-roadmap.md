# ChainSentinel — 30-Day Development Roadmap

**Audience:** Solo developer learning by building  
**Goal:** From empty scaffold to working MVP slice (scan → finding → dashboard)  
**Method:** Daily milestones with verification gates — no tutorial watching required

---

## How to Use This Roadmap

1. Complete [Local Development Setup](./09-local-development-setup.md) before Day 1
2. Each day has **Build**, **Learn**, and **Verify** sections
3. Do not skip verification — it builds professional habits
4. Reference architecture docs when making design decisions

---

## Week 1 — Foundation & First Run (Days 1–7)

### Day 1 — Environment & Repository

| Build | Learn | Verify |
|-------|-------|--------|
| Run `verify-environment.ps1`, install missing tools | Why each tool exists in the stack | All tools green in verify script |
| `git init`, first commit with scaffold | Git branching strategy | `git log` shows clean history |
| Start Docker Postgres | Docker networking basics | `docker compose ps` shows healthy postgres |

**Outcome:** Machine verified, repo initialized, database running.

---

### Day 2 — Backend Skeleton

| Build | Learn | Verify |
|-------|-------|--------|
| Run backend init commands | FastAPI project structure | `GET /health` returns 200 |
| Configure SQLAlchemy + asyncpg | Async Python DB patterns | DB connection test passes |
| Create `organizations` migration | PostgreSQL migrations with Alembic | `\dt` in psql shows tables |

**Outcome:** FastAPI serves `/health` and connects to PostgreSQL.

---

### Day 3 — Frontend Skeleton

| Build | Learn | Verify |
|-------|-------|--------|
| Run frontend init (Next.js 15 + ShadCN) | App Router vs Pages Router | `localhost:3000` loads |
| Create layout shell (sidebar, header) | TailwindCSS utility patterns | Responsive at mobile width |
| Connect to backend `/health` | Server vs client components | Status badge shows "Connected" |

**Outcome:** Dashboard shell talks to API.

---

### Day 4 — Smart Contracts Baseline

| Build | Learn | Verify |
|-------|-------|--------|
| Init Hardhat + Foundry in `contracts/` | Hardhat vs Foundry roles | `forge test` passes sample test |
| Write `AttestationAnchor.sol` stub | Solidity 0.8.x basics | `hardhat compile` succeeds |
| Run local Hardhat node | JSON-RPC, chain ID 31337 | `curl` eth_blockNumber works |

**Outcome:** Local chain running, contracts compile.

---

### Day 5 — Domain Models

| Build | Learn | Verify |
|-------|-------|--------|
| Implement Project, Deployment models | Multi-tenant data modeling | Alembic migration applies |
| CRUD routes: `/v1/projects` | REST design from docs/04 | Postman/curl CRUD works |
| Pydantic schemas + validation | Input validation patterns | Invalid payload returns 422 |

**Outcome:** Projects API complete with tests.

---

### Day 6 — Frontend Projects UI

| Build | Learn | Verify |
|-------|-------|--------|
| Projects list page with ShadCN Table | Data fetching with TanStack Query | Lists projects from API |
| Create project dialog | Form validation (zod) | New project appears in list |
| Loading and error states | UX for async operations | Network error shows toast |

**Outcome:** End-to-end project creation from UI.

---

### Day 7 — Week 1 Review

| Build | Learn | Verify |
|-------|-------|--------|
| Write 5 integration tests | pytest + httpx AsyncClient | `pytest tests/integration` green |
| Fix tech debt from week | Refactoring discipline | CI workflow passes on push |
| Update README with progress | Documentation as code | README accurate |

**Outcome:** Week 1 checkpoint — project CRUD E2E working.

---

## Week 2 — Deployments & Static Analysis (Days 8–14)

### Day 8 — Deployment Registration

Register contract addresses per project. Implement `deployments` table and API per `docs/03-database-schema.md`.

**Verify:** Register Sepolia or local address via API and UI.

---

### Day 9 — ABI & Metadata Storage

Upload ABI JSON, store compiler metadata. Learn ABI encoding basics.

**Verify:** `GET /deployments/{id}/abi` returns stored ABI.

---

### Day 10 — Scan Job Model

Create `scans` and `findings` tables. Scan job queue (in-process first, Celery later).

**Verify:** `POST /deployments/{id}/scans` returns 202 with scan ID.

---

### Day 11 — Slither Integration (Subprocess)

Invoke Slither in subprocess from FastAPI worker. Parse JSON output.

**Verify:** Scan completes on sample vulnerable contract; findings persisted.

---

### Day 12 — Finding Normalization

Map Slither output to ChainSentinel finding schema (severity, SWC, fingerprint).

**Verify:** Re-scan deduplicates by fingerprint.

---

### Day 13 — Findings UI

Findings table with severity badges, filters, detail drawer with code location.

**Verify:** UI shows findings from Day 11 scan.

---

### Day 14 — Week 2 Review

CI runs backend + contract tests. Document scan pipeline in `docs/`.

**Verify:** Full scan flow demo recordable in 2 minutes.

---

## Week 3 — Risk & Monitoring Basics (Days 15–21)

### Day 15 — Rules-Only Risk Score

Implement static analysis dimension from `docs/06-risk-scoring-engine.md`.

**Verify:** `GET /deployments/{id}/risk` returns score + breakdown.

---

### Day 16 — Risk Dashboard

Charts: severity distribution, score gauge (ShadCN + recharts).

**Verify:** Dashboard updates after new scan.

---

### Day 17 — Ethers.js Chain Reader

Read contract code, detect proxy pattern from backend.

**Verify:** Proxy detection logged for upgradeable contract.

---

### Day 18 — Block Polling Worker

Poll local Hardhat node for txs touching monitored addresses.

**Verify:** Transfer to monitored contract triggers log entry.

---

### Day 19 — Alert Rules CRUD

Simple rule: "open critical finding → alert".

**Verify:** Alert row created when critical finding exists.

---

### Day 20 — Slack/Webhook Notifier Stub

Log webhook payload to console (real Slack in Phase 2).

**Verify:** Alert triggers payload in backend logs.

---

### Day 21 — Week 3 Review

Integration test: scan → score → alert pipeline.

**Verify:** Single pytest covers full pipeline.

---

## Week 4 — AI Reports & Polish (Days 22–30)

### Day 22 — Ollama Integration

FastAPI service calls Ollama `/api/generate` with Qwen 3.

**Verify:** `ollama run qwen3:4b "Hello"` and API wrapper both work.

---

### Day 23 — Report Job Model

`reports` and `report_sections` tables. Template-only report (no AI).

**Verify:** PDF/Markdown report generated from findings JSON.

---

### Day 24 — AI Executive Summary

RAG-free first version: prompt with findings JSON, guardrail schema validation.

**Verify:** Summary cites finding IDs; no invented vulnerabilities.

---

### Day 25 — Report UI

Generate report button, status polling, download link.

**Verify:** Report downloadable from dashboard.

---

### Day 26 — On-Chain Attestation (Local)

Deploy `AttestationAnchor` to Hardhat, anchor report hash.

**Verify:** `getAttestation()` returns matching hash.

---

### Day 27 — Ethers.js Frontend Wallet Read

Connect MetaMask read-only, display network/address (no transactions yet).

**Verify:** Wallet address shown in UI.

---

### Day 28 — Docker Full Stack

Optional: dockerize backend for integration tests.

**Verify:** `docker compose up` + API health check.

---

### Day 29 — Security Hardening Pass

CORS lockdown, env validation, rate limit middleware, `.env` audit.

**Verify:** OWASP basic checklist completed (document in `docs/`).

---

### Day 30 — MVP Demo & Retrospective

| Deliverable | Criteria |
|-------------|----------|
| Create project | ✓ |
| Register deployment | ✓ |
| Run scan | ✓ |
| View findings | ✓ |
| See risk score | ✓ |
| Generate AI report | ✓ |
| Anchor hash locally | ✓ |

Write retrospective: what to refactor, what to defer to Phase 2 per `docs/08-development-roadmap.md`.

---

## Daily Time Budget

| Experience Level | Hours/Day |
|------------------|-----------|
| Full-time focus | 6–8 |
| Part-time | 2–3 (extend to 60-day pace) |

---

## When Blocked

1. Run `verify-environment.ps1`
2. Check relevant architecture doc in `docs/`
3. Reduce scope — ship thin vertical slice, refine later

---

## Related Documents

- [Platform Roadmap (18-month)](./08-development-roadmap.md)
- [Local Development Setup](./09-local-development-setup.md)
- [API Endpoints](./04-api-endpoints.md)
