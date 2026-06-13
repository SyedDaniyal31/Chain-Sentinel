# ChainSentinel Backend

FastAPI application server for ChainSentinel.

## Setup

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

## Run (after implementing app.main)

```powershell
uvicorn app.main:app --reload --port 8000
```

## Verify

```powershell
curl http://localhost:8000/health
```

Application code not yet implemented — see `docs/12-30-day-roadmap.md` Day 2.
