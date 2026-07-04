# ChainSentinel Backend

FastAPI application server for ChainSentinel.

## Structure

```
app/
├── main.py          # App factory, middleware, lifespan
├── api/             # HTTP routes (thin handlers)
│   ├── health.py    # GET /health
│   └── v1/          # Scans and chains API
├── services/        # Business logic
├── models/          # SQLAlchemy ORM
├── schemas/         # Pydantic request/response
├── core/            # Config, logging, validators
└── db/              # Engine, sessions, Base
```

## Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

## Run

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Verify

```powershell
curl http://localhost:8000/health

curl -X POST http://localhost:8000/api/v1/scans `
  -H "Content-Type: application/json" `
  -d '{"scan_type":"wallet","target_address":"0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"}'

pytest
alembic upgrade head
```

OpenAPI docs: http://localhost:8000/docs

Migrations: see [docs/MIGRATIONS.md](docs/MIGRATIONS.md)
