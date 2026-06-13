-- ChainSentinel — PostgreSQL bootstrap script
-- Runs once on first container start via docker-entrypoint-initdb.d

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Application schema (minimal bootstrap — full schema via Alembic migrations)
CREATE SCHEMA IF NOT EXISTS chainsentinel;

-- Dev-only audit: confirm init ran
CREATE TABLE IF NOT EXISTS chainsentinel.schema_bootstrap (
    id          SERIAL PRIMARY KEY,
    version     VARCHAR(32) NOT NULL DEFAULT '1.0.0',
    applied_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO chainsentinel.schema_bootstrap (version) VALUES ('1.0.0');

-- Grant permissions to app user
GRANT ALL PRIVILEGES ON SCHEMA chainsentinel TO chainsentinel;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA chainsentinel TO chainsentinel;
ALTER DEFAULT PRIVILEGES IN SCHEMA chainsentinel GRANT ALL ON TABLES TO chainsentinel;
