# ChainSentinel

**Blockchain Security Intelligence Platform**

ChainSentinel unifies smart contract analysis, runtime intelligence, risk scoring, protocol scanning, and continuous security monitoring into a single platform for protocol teams and security researchers.

---

## Current Status

| Layer | Status | Stack |
|-------|--------|-------|
| **Backend API** | Implemented | Python 3.12, FastAPI, SQLAlchemy, Alembic |
| **Frontend** | Implemented | Next.js 15, TypeScript, Tailwind CSS |
| **Database** | Implemented | PostgreSQL 16 (Docker) |
| **Security engines** | Implemented | Contract/wallet analyzers, risk engine, runtime intelligence (M9), protocol scan (M8) |
| **Continuous monitoring** | Library complete (M10) | Watch registry → change detection → re-analysis → risk delta → alerts → history |
| **Contracts** | Scaffold | Solidity, Hardhat, Foundry |
| **Infrastructure** | Dev-ready | Docker Compose (Postgres, Redis), GitHub Actions CI |

**Test suite:** 522 backend unit/integration tests (`backend/tests/`).

The **production API** today exposes on-demand wallet and contract scanning. The **continuous monitoring pipeline** is implemented as backend libraries under `backend/app/blockchain/continuous/`; API and scheduler integration are planned in the [development roadmap](./docs/08-development-roadmap.md).

---

## Features (Implemented)

### On-demand scanning (API + dashboard)

- `POST /api/v1/scans` — queue wallet or contract analysis
- `GET /api/v1/scans`, `/scans/{id}`, `/scans/summary` — history and results
- `GET /api/v1/chains` — supported chain list
- Contract analysis: proxy detection, governance, capabilities, honeypot simulation, liquidity, wallet intelligence, protocol intelligence
- Risk evidence model (M7) with correlation engine and executive protocol reports (M8.4)

### Runtime intelligence (M9)

- Transaction intelligence, call trace intelligence, state transition intelligence, exploit simulation

### Continuous security platform (M10 — library)

- Watch registry, snapshot change detection, selective re-analysis, risk delta, alert engine, baseline history & timeline

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Node.js | 20.x or 22.x LTS | Frontend |
| Python | **3.12.x** | Backend |
| Docker Desktop | Latest | PostgreSQL, Redis |
| Git | ≥ 2.40 | Version control |
| Foundry | Latest (optional) | Trade simulation, contract tests |

See [Local Development Setup](./docs/09-local-development-setup.md) for full installation.

---

## Quick Start

### 1. Start infrastructure

```powershell
docker compose -f docker/docker-compose.yml up -d
```

### 2. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-dev.txt
Copy-Item .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

OpenAPI (development): http://localhost:8000/docs

### 3. Frontend

```powershell
cd frontend
npm ci
Copy-Item .env.local.example .env.local   # if present
npm run dev
```

Dashboard: http://localhost:3000

### 4. Run tests

```powershell
cd backend
pytest -q
```

---

## Repository Structure

```
ChainSentinel/
├── backend/           # FastAPI app, analyzers, blockchain engines
│   └── app/blockchain/
│       ├── runtime/       # M9 transaction/trace/state/simulation
│       ├── risk/          # M7 evidence & correlation
│       ├── protocol_scan/ # M8 discovery & scheduling
│       └── continuous/    # M10 watch → alert → history
├── frontend/          # Next.js dashboard
├── contracts/         # Solidity test contracts
├── database/          # PostgreSQL init SQL
├── docker/            # Docker Compose (Postgres, Redis)
├── docs/              # Architecture and setup documentation
├── scripts/           # Environment verify & setup scripts
└── .github/workflows/ # CI pipeline
```

---

## API (v1)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Service health |
| `GET` | `/api/v1/chains` | Supported chains |
| `POST` | `/api/v1/scans` | Create scan job |
| `GET` | `/api/v1/scans` | Paginated scan history |
| `GET` | `/api/v1/scans/{id}` | Scan job + result |
| `GET` | `/api/v1/scans/summary` | Aggregate statistics |

Full request/response schemas: `http://localhost:8000/docs` (non-production environments).

---

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture Index](./docs/README.md) | Documentation map |
| [System Architecture](./docs/02-system-architecture.md) | Platform topology |
| [Development Roadmap](./docs/08-development-roadmap.md) | Phased delivery plan |
| [Local Development Setup](./docs/09-local-development-setup.md) | Tooling & environment |
| [Docker Architecture](./docs/10-docker-architecture.md) | Container stack |
| [Database Migrations](./backend/docs/MIGRATIONS.md) | Alembic workflow |

See [docs/README.md](./docs/README.md) for the full documentation index.

---

## Environment Variables

```powershell
Copy-Item backend\.env.example backend\.env
```

Key settings:

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL connection |
| `ETH_RPC_URL` / `CHAIN_ID` | Primary chain RPC |
| `ETHERSCAN_API_KEY` | Verified source lookup (optional) |
| `DB_AUTO_CREATE_TABLES` | Dev only; use `false` + Alembic in production |
| `CORS_ORIGINS` | Frontend origin(s) |

Never commit `.env` files.

---

## Production Notes

Before deploying:

1. Set `APP_ENV=production`, `APP_DEBUG=false`, `DB_AUTO_CREATE_TABLES=false`
2. Run `alembic upgrade head` on PostgreSQL
3. Configure authentication and rate limiting (planned — see roadmap)
4. Use dedicated RPC endpoints with API keys

---

## License

TBD — Add license before public release.
