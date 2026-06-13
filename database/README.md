# Database

PostgreSQL schema and migrations for ChainSentinel.

## Local Database (Docker)

```powershell
docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up -d postgres
```

## Connect

| Method | Command / URL |
|--------|---------------|
| Adminer | http://localhost:8080 (server: `postgres`) |
| psql | `psql -h localhost -U chainsentinel -d chainsentinel` |

## Files

| Path | Purpose |
|------|---------|
| `init.sql` | First-boot bootstrap (extensions, schema) |
| `migrations/` | Alembic migrations (created Day 2) |
| `seeds/` | Dev seed data |

Full schema: `docs/03-database-schema.md`
