# Database Migration Strategy — ChainSentinel Backend

## Overview

ChainSentinel uses **Alembic** for schema versioning and **SQLAlchemy async** for runtime access. Never edit production databases by hand.

## Environments

| Environment | Table creation | Tool |
|-------------|----------------|------|
| **Local dev** | `DB_AUTO_CREATE_TABLES=true` (default) OR Alembic | Fast bootstrap |
| **Staging / Production** | Alembic only | `DB_AUTO_CREATE_TABLES=false` |

## Workflow

### 1. Change the ORM model

Edit files under `app/models/`, then generate a migration:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
alembic revision --autogenerate -m "describe change"
```

Review the generated file in `alembic/versions/` before applying.

### 2. Apply migrations

```powershell
alembic upgrade head
```

### 3. Roll back one revision

```powershell
alembic downgrade -1
```

### 4. Check current revision

```powershell
alembic current
alembic history
```

## Initial migration

Revision `001_create_scan_jobs_table` creates the `scan_jobs` table matching `app.models.scan_job.ScanJob`.

Apply after PostgreSQL is running:

```powershell
docker compose -f ../docker/docker-compose.yml up -d postgres
alembic upgrade head
```

## Rules

1. **One migration per logical change** — easier review and rollback.
2. **Never delete applied migrations** — add a new migration to revert.
3. **Review autogenerate output** — Alembic can miss renames (drop + add instead).
4. **Backup before production upgrades** — pg_dump snapshot.
5. **Disable auto-create in production** — set `DB_AUTO_CREATE_TABLES=false`.

## CI integration

GitHub Actions should run:

```yaml
- run: alembic upgrade head
  env:
    DATABASE_URL: postgresql+asyncpg://...
```

before backend integration tests.
