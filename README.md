# ChainSentinel

**Blockchain Security Intelligence Platform**

ChainSentinel unifies smart contract analysis, on-chain monitoring, risk scoring, and AI-assisted security reporting into a single platform for protocol teams and security researchers.

---

## Status

| Layer | Status | Stack |
|-------|--------|-------|
| Frontend | Scaffold ready | Next.js 15, TypeScript, TailwindCSS, ShadCN UI |
| Backend | Scaffold ready | Python, FastAPI |
| Database | Docker-ready | PostgreSQL 16 |
| Contracts | Scaffold ready | Solidity, Hardhat, Foundry |
| AI | Local inference | Ollama + Qwen 3 |
| DevOps | Configured | Docker Compose, GitHub Actions |

> Application code is not yet implemented. This repository contains architecture docs, environment configuration, and initialization scripts.

---

## Prerequisites

| Tool | Required Version | Purpose |
|------|------------------|---------|
| Node.js | 20.x or 22.x LTS (≥18.18) | Frontend, Hardhat, tooling |
| Python | **3.12.x** (recommended) | FastAPI backend |
| Git | ≥2.40 | Version control |
| Docker Desktop | Latest | PostgreSQL, Redis, local stack |
| PostgreSQL | 16+ (via Docker) | Primary datastore |
| Ollama | Latest | Local LLM inference |
| Foundry | Latest | Solidity testing & deployment |
| Hardhat | 3.x | JS toolchain for contracts |

See [Local Development Setup](./docs/09-local-development-setup.md) for full installation instructions.

---

## Quick Start

### 1. Verify your environment

```powershell
cd D:\ChainSentinel
.\scripts\verify-environment.ps1
```

### 2. Install missing tools (Windows)

```powershell
# Run PowerShell as Administrator
.\scripts\setup-windows.ps1
```

### 3. Initialize project scaffolds (when ready to build)

```powershell
.\scripts\init-project.ps1
```

### 4. Start infrastructure

```powershell
docker compose -f docker/docker-compose.yml up -d
```

### 5. Start development servers (after init)

```powershell
# Terminal 1 — Backend
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend
npm run dev

# Terminal 3 — Local chain (after contracts init)
cd contracts
npx hardhat node
```

---

## Repository Structure

```
ChainSentinel/
├── frontend/          # Next.js 15 dashboard
├── backend/           # FastAPI API server
├── contracts/         # Solidity + Hardhat + Foundry
├── database/          # Migrations, seeds, init SQL
├── docker/            # Docker Compose & service configs
├── docs/              # Architecture & setup documentation
├── scripts/           # Setup, verify, init automation
├── tests/             # Cross-stack integration & E2E
├── .github/           # GitHub Actions CI/CD
├── .gitignore
└── README.md
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture Index](./docs/README.md) | Platform architecture overview |
| [Local Development Setup](./docs/09-local-development-setup.md) | Tool installation & verification |
| [Docker Architecture](./docs/10-docker-architecture.md) | Container topology |
| [GitHub Actions CI/CD](./docs/11-github-actions-cicd.md) | Pipeline design |
| [30-Day Roadmap](./docs/12-30-day-roadmap.md) | Learning-by-building plan |

---

## Environment Variables

Copy the root template and per-service examples:

```powershell
Copy-Item .env.example .env
Copy-Item frontend\.env.local.example frontend\.env.local
Copy-Item backend\.env.example backend\.env
```

Never commit `.env` files. See `.env.example` for all variables.

---

## Security

- Do not commit private keys, API secrets, or `.env` files
- Use Hardhat/Anvil default accounts **only** for local development
- Rotate `API_SECRET_KEY` before any deployment

---

## License

TBD — Add license before public release.

---

## Contributing

1. Run `.\scripts\verify-environment.ps1` before opening a PR
2. Follow conventions in [docs/01-folder-structure.md](./docs/01-folder-structure.md)
3. Keep architecture docs updated when changing system boundaries
