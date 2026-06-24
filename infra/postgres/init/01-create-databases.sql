-- PartFlow Postgres bootstrap.
-- Runs once on first container start (empty data dir), as POSTGRES_USER against POSTGRES_DB.
-- Creates the side databases/roles that Airflow and Metabase need so the single
-- Postgres instance can back all three concerns. The warehouse db (partflow) and its
-- owner are created by the image from POSTGRES_DB/POSTGRES_USER.

-- ── Airflow metadata ────────────────────────────────────────────────────────
CREATE ROLE airflow WITH LOGIN PASSWORD 'airflow';
CREATE DATABASE airflow OWNER airflow;

-- ── Metabase application database ───────────────────────────────────────────
CREATE ROLE metabase WITH LOGIN PASSWORD 'metabase';
CREATE DATABASE metabase OWNER metabase;

-- ── Read-only role for the web app / BI (warehouse access only) ─────────────
-- Privileges on future mart tables are granted in Phase 7 once schemas exist.
CREATE ROLE partflow_ro WITH LOGIN PASSWORD 'partflow_ro';
GRANT CONNECT ON DATABASE partflow TO partflow_ro;
