-- Runs once on first container start (empty pgdata volume).
-- POSTGRES_USER=arxi already owns the arxi database.

-- Schemas used by alembic migrations
CREATE SCHEMA IF NOT EXISTS arxi AUTHORIZATION arxi;
CREATE SCHEMA IF NOT EXISTS compliance AUTHORIZATION arxi;

-- Ensure arxi can create tables in public (for users + alembic_version)
GRANT ALL ON SCHEMA public TO arxi;
