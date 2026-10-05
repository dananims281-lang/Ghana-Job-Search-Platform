-- Migration 003: add profile fields to company (for GET/POST /companies).
--
-- Only needed if your database already has the company table.
-- On a fresh database, skip this; starting the app creates the table with these columns.
--
-- Run with:  psql ghana_jobs -f migrations/003_expand_company.sql

BEGIN;

ALTER TABLE company
    ADD COLUMN IF NOT EXISTS description TEXT,
    ADD COLUMN IF NOT EXISTS country     VARCHAR(2),
    ADD COLUMN IF NOT EXISTS region      VARCHAR(100),
    ADD COLUMN IF NOT EXISTS city        VARCHAR(100),
    ADD COLUMN IF NOT EXISTS created_at  TIMESTAMPTZ NOT NULL DEFAULT now();

COMMIT;
