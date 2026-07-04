# ChainSentinel — Local Development Setup

**Version:** 1.0.0  
**Last verified:** 2026-06-13  
**Platform:** Windows 11 (primary), with notes for cross-platform

---

## 1. Detected System Profile

Run `.\scripts\verify-environment.ps1` to refresh this section on your machine.

| Component | Detected Value | Impact |
|-----------|----------------|--------|
| OS | Windows 11 Pro (Build 26200) | Use PowerShell scripts, Docker Desktop |
| CPU | Intel i7-1185G7 (4C/8T) | Adequate for dev; Foundry tests parallelize well |
| RAM | 16 GB | Limit Ollama model size; cap Docker memory |
| GPU | Intel Iris Xe (integrated) | Ollama runs CPU inference; use small Qwen models |
| Virtualization | Enabled | Docker Desktop compatible |

---

## 2. Tool Matrix

| Tool | Required | Recommended Version | Your Status | Why Needed |
|------|----------|---------------------|-------------|------------|
| **Git** | Yes | ≥2.40 | Verify with script | Version control, CI |
| **Node.js** | Yes | 22.x LTS | Verify with script | Next.js, Hardhat, Ethers.js |
| **npm** | Yes | ≥10 | Bundled with Node | Package management |
| **Python** | Yes | **3.12.x** | Verify with script | FastAPI backend |
| **Docker Desktop** | Yes | Latest | Verify with script | PostgreSQL, Redis locally |
| **PostgreSQL client** | Optional | 16+ | Via Docker or `psql` | DB debugging |
| **Ollama** | Yes | Latest | Verify with script | Local Qwen 3 inference |
| **Foundry** | Yes | Latest | Verify with script | Solidity test/deploy |
| **Hardhat** | Yes | 3.x | Project-local | JS contract toolchain |
| **MetaMask** | Recommended | Browser ext | Manual install | Wallet testing (Day 27+) |
| **WSL 2** | Recommended | Ubuntu 22.04 | Verify with script | Foundry performance, optional |

---

## 3. Compatibility Notes (Critical)

### 3.1 Node.js vs Next.js 15

- **Required:** Node ≥ 18.18.0
- **Recommended:** Node **22.x LTS** (best ecosystem stability)
- Node 24.x works but is current — pin via `.node-version`

**Verify:**
```powershell
node --version   # expect v22.x or v20.x
```

### 3.2 Python Version — IMPORTANT

- **Recommended:** Python **3.12.x** for backend
- Python 3.14 is bleeding-edge — many packages (`asyncpg`, `pydantic`, `uvicorn`) may lack wheels or behave unexpectedly
- Keep 3.14 if installed, but create backend venv with 3.12

**Verify:**
```powershell
py -0p                    # list installed Python versions
py -3.12 --version          # should exist after setup
```

### 3.3 Ollama + Qwen 3 on 16 GB RAM

| Model | RAM Usage | Speed | Recommendation |
|-------|-----------|-------|----------------|
| `qwen3:4b` | ~3–4 GB | Fast (CPU) | **Primary dev model** |
| `qwen3:8b` | ~5–6 GB | Moderate | Use when 8+ GB free |
| `qwen3:14b+` | 10+ GB | Slow | **Not recommended** on this hardware |

Integrated Intel GPU provides limited Ollama acceleration on Windows — expect **CPU inference**.

**Verify:**
```powershell
ollama --version
ollama list
ollama run qwen3:4b "Summarize reentrancy attacks in one sentence."
```

### 3.4 Foundry on Windows

Foundry (`forge`, `cast`, `anvil`) runs natively on Windows but **performs best in WSL 2**. Native Windows install via `foundryup` is supported.

**Verify:**
```powershell
forge --version
cast --version
anvil --version
```

---

## 4. Installation Guide (Windows)

Run PowerShell **as Administrator** for system-level installs.

### 4.1 Automated Setup

```powershell
cd D:\ChainSentinel
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\setup-windows.ps1
```

### 4.2 Manual Install Commands

#### Git (if missing)
```powershell
winget install --id Git.Git -e --accept-source-agreements --accept-package-agreements
```
**Verify:** `git --version`

#### Node.js 22 LTS (recommended alongside existing Node)
```powershell
winget install --id OpenJS.NodeJS.LTS -e --accept-source-agreements --accept-package-agreements
```
**Verify:** `node --version` → v22.x

#### Python 3.12 (backend)
```powershell
winget install --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements
```
**Verify:** `py -3.12 --version`

#### Docker Desktop
```powershell
winget install --id Docker.DockerDesktop -e --accept-source-agreements --accept-package-agreements
```
**After install:** Reboot, enable WSL 2 backend in Docker settings.

**Verify:**
```powershell
docker --version
docker compose version
docker run hello-world
```

#### WSL 2 (recommended for Foundry + Docker)
```powershell
wsl --install -d Ubuntu-22.04
```
**Reboot required.** Set Docker Desktop → Settings → General → Use WSL 2 based engine.

**Verify:** `wsl --status`

#### Ollama
```powershell
winget install --id Ollama.Ollama -e --accept-source-agreements --accept-package-agreements
```
**Pull Qwen 3 model:**
```powershell
ollama pull qwen3:4b
ollama pull qwen3:8b    # optional, higher quality
```
**Verify:** `ollama list`

#### Foundry
```powershell
# Native Windows (PowerShell)
irm https://getfoundry.sh | iex
foundryup
```
**Verify:** `forge --version`

#### MetaMask (browser — manual)

1. Install [MetaMask extension](https://metamask.io/download/) in Chrome/Brave/Edge
2. Create a **separate dev wallet** — never use mainnet funds
3. Add local network: RPC `http://127.0.0.1:8545`, Chain ID `31337`

**Verify:** MetaMask shows account address on local Hardhat network

#### PostgreSQL Client (optional — psql CLI)
```powershell
winget install --id PostgreSQL.PostgreSQL.16 -e --accept-source-agreements --accept-package-agreements
```
Or use Adminer at `http://localhost:8080` via Docker.

---

## 5. Project Initialization Commands

Run **after** environment verification passes:

```powershell
cd D:\ChainSentinel
.\scripts\init-project.ps1
```

### 5.1 Frontend (manual reference)

```powershell
cd frontend
npx create-next-app@15 . --typescript --tailwind --eslint --app --src-dir --import-alias "@/*" --use-npm --yes
npx shadcn@latest init --defaults --yes
npm install ethers
```

### 5.2 Backend (manual reference)

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
alembic init alembic   # when implementing migrations
```

### 5.3 Smart Contracts (manual reference)

```powershell
cd contracts
npm init -y
npm install --save-dev hardhat @nomicfoundation/hardhat-toolbox ethers
npx hardhat init
forge init foundry --no-commit --force
npm install ethers
```

### 5.4 Database (manual reference)

```powershell
cd D:\ChainSentinel
docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up -d
docker compose -f docker/docker-compose.yml ps
```

### 5.5 Environment files

```powershell
Copy-Item .env.example .env
Copy-Item backend\.env.example backend\.env -ErrorAction SilentlyContinue
Copy-Item frontend\.env.local.example frontend\.env.local -ErrorAction SilentlyContinue
```

---

## 6. Performance Tuning (16 GB RAM)

| Setting | Value | Why |
|---------|-------|-----|
| Docker Desktop memory | 4 GB max | Leave RAM for Ollama + IDE |
| Ollama model | `qwen3:4b` default | Fits alongside Docker + Chrome |
| Cursor/IDE | Close unused extensions | Reduce baseline memory |
| Hardhat node | Single instance | Avoid duplicate local chains |
| WSL 2 memory | `.wslconfig` limit 4GB | Prevent WSL consuming all RAM |

Create `%USERPROFILE%\.wslconfig`:
```ini
[wsl2]
memory=4GB
processors=4
swap=2GB
```

Create `%USERPROFILE%\.ollama\config` (if needed):
```
OLLAMA_MAX_LOADED_MODELS=1
OLLAMA_NUM_PARALLEL=1
```

---

## 7. Cursor IDE Configuration

Recommended extensions (`.vscode/extensions.json`):

- ESLint
- Prettier
- Tailwind CSS IntelliSense
- Python (Microsoft)
- Pylance
- Solidity (NomicFoundation)
- Docker
- GitLens

---

## 8. Full Verification Checklist

```powershell
.\scripts\verify-environment.ps1 -Detailed
```

Expected: all critical tools PASS before starting Day 1 of roadmap.

---

## 9. Troubleshooting

| Issue | Fix |
|-------|-----|
| `docker` not found after install | Reboot; ensure Docker Desktop is running |
| Port 5432 in use | Stop local PostgreSQL service or change `POSTGRES_PORT` |
| `forge` not found | Re-run `foundryup`; restart terminal |
| Ollama slow | Use `qwen3:4b`; close other apps |
| Python packages fail on 3.14 | Use `py -3.12 -m venv .venv` |
| WSL not installed | Run `wsl --install`, reboot |

---

## 10. Related Documents

- [Docker Architecture](./10-docker-architecture.md)
- [Development Roadmap](./08-development-roadmap.md)
- [GitHub Actions CI/CD](./11-github-actions-cicd.md)
