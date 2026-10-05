-- Migration 001: expand job_listing to match the new job response shape.
--
-- Only needed if your database already has the OLD company / job_listing tables.
-- On a fresh database, just start the app: Base.metadata.create_all creates the new tables.
--
-- Run with:  psql myapp -f migrations/001_expand_job_listing.sql
--
-- Existing rows are backfilled with these assumptions (review them afterwards):
--   * country = 'GH', salary currency = 'GHS', salary period = 'yearly'
--   * category = 'other', employment_type = 'full_time'
--   * old "location" text containing "remote" -> work_mode 'remote', otherwise 'onsite' with city = old text
--   * old single "salary" -> both salary_min and salary_max

BEGIN;

-- ---------- company ----------
ALTER TABLE company ADD COLUMN IF NOT EXISTS website VARCHAR(500);

-- ---------- job_listing: add new columns (nullable first so we can backfill) ----------
ALTER TABLE job_listing
    ADD COLUMN category         VARCHAR(50),
    ADD COLUMN employment_type  VARCHAR(20),
    ADD COLUMN experience_level VARCHAR(20),
    ADD COLUMN work_mode        VARCHAR(20),
    ADD COLUMN country          VARCHAR(2),
    ADD COLUMN region           VARCHAR(100),
    ADD COLUMN city             VARCHAR(100),
    ADD COLUMN salary_min       INTEGER,
    ADD COLUMN salary_max       INTEGER,
    ADD COLUMN salary_currency  VARCHAR(3),
    ADD COLUMN salary_period    VARCHAR(20),
    ADD COLUMN requirements     TEXT[] NOT NULL DEFAULT '{}',
    ADD COLUMN benefits         TEXT[] NOT NULL DEFAULT '{}',
    ADD COLUMN updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    ADD COLUMN expires_at       TIMESTAMPTZ;

-- ---------- backfill existing rows ----------
UPDATE job_listing SET
    category        = 'other',
    employment_type = 'full_time',
    country         = 'GH',
    work_mode       = CASE WHEN location ILIKE '%remote%' THEN 'remote' ELSE 'onsite' END,
    city            = CASE WHEN location ILIKE '%remote%' THEN NULL ELSE LEFT(location, 100) END,
    description     = COALESCE(description, '');

UPDATE job_listing SET
    salary_min      = ROUND(salary)::INTEGER,
    salary_max      = ROUND(salary)::INTEGER,
    salary_currency = 'GHS',
    salary_period   = 'yearly'
WHERE salary IS NOT NULL;

-- ---------- created_at -> posted_at (timezone-aware; old values were stored as UTC) ----------
ALTER TABLE job_listing RENAME COLUMN created_at TO posted_at;
ALTER TABLE job_listing
    ALTER COLUMN posted_at TYPE TIMESTAMPTZ USING posted_at AT TIME ZONE 'UTC',
    ALTER COLUMN posted_at SET DEFAULT now();

-- ---------- tighten columns ----------
ALTER TABLE job_listing
    ALTER COLUMN title           TYPE VARCHAR(150),
    ALTER COLUMN description     SET NOT NULL,
    ALTER COLUMN category        SET NOT NULL,
    ALTER COLUMN employment_type SET NOT NULL,
    ALTER COLUMN work_mode       SET NOT NULL,
    ALTER COLUMN country         SET NOT NULL,
    ALTER COLUMN status          TYPE VARCHAR(20);

-- ---------- drop old columns ----------
ALTER TABLE job_listing
    DROP COLUMN location,
    DROP COLUMN salary;

-- ---------- constraints ----------
ALTER TABLE job_listing
    ADD CONSTRAINT ck_job_listing_employment_type
        CHECK (employment_type IN ('full_time', 'part_time', 'contract', 'internship', 'temporary')),
    ADD CONSTRAINT ck_job_listing_experience_level
        CHECK (experience_level IN ('entry', 'mid', 'senior', 'lead')),
    ADD CONSTRAINT ck_job_listing_status
        CHECK (status IN ('draft', 'open', 'closed')),
    ADD CONSTRAINT ck_job_listing_work_mode
        CHECK (work_mode IN ('onsite', 'hybrid', 'remote')),
    ADD CONSTRAINT ck_job_listing_salary_period
        CHECK (salary_period IN ('hourly', 'monthly', 'yearly')),
    ADD CONSTRAINT ck_job_listing_salary_range
        CHECK (salary_min IS NULL OR salary_max IS NULL OR salary_min <= salary_max);

-- ---------- indexes (used by search filters) ----------
CREATE INDEX IF NOT EXISTS ix_job_listing_company_id ON job_listing (company_id);
CREATE INDEX IF NOT EXISTS ix_job_listing_category   ON job_listing (category);
CREATE INDEX IF NOT EXISTS ix_job_listing_status     ON job_listing (status);
CREATE INDEX IF NOT EXISTS ix_job_listing_country    ON job_listing (country);
CREATE INDEX IF NOT EXISTS ix_job_listing_city       ON job_listing (city);

COMMIT;
