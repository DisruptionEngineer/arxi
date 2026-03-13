-- Runs once on first container start (empty pgdata volume).
-- POSTGRES_USER=arxi is the superuser and owns the arxi database.
-- These are belt-and-suspenders grants to ensure migrations always work.

-- Schemas used by alembic migrations
CREATE SCHEMA IF NOT EXISTS arxi AUTHORIZATION arxi;
CREATE SCHEMA IF NOT EXISTS compliance AUTHORIZATION arxi;

-- Ensure arxi can create tables/types in public (users + alembic_version + enums)
GRANT ALL ON SCHEMA public TO arxi;
GRANT CREATE ON SCHEMA public TO arxi;
