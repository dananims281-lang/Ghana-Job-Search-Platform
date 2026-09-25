-- Migration 002: rename table job_listing -> jobs (API path is now /jobs).
--
-- Run after 001, only on a database that already has the job_listing table:
--   psql myapp -f migrations/002_rename_job_listing_to_jobs.sql
-- On a fresh database, skip this; starting the app creates the jobs table directly.

BEGIN;

ALTER TABLE job_listing RENAME TO jobs;

-- Rename keys, checks and indexes so they match what the app creates on a fresh database
ALTER TABLE jobs RENAME CONSTRAINT job_listing_pkey            TO jobs_pkey;
ALTER TABLE jobs RENAME CONSTRAINT job_listing_company_id_fkey TO jobs_company_id_fkey;

ALTER TABLE jobs RENAME CONSTRAINT ck_job_listing_employment_type  TO ck_jobs_employment_type;
ALTER TABLE jobs RENAME CONSTRAINT ck_job_listing_experience_level TO ck_jobs_experience_level;
ALTER TABLE jobs RENAME CONSTRAINT ck_job_listing_status           TO ck_jobs_status;
ALTER TABLE jobs RENAME CONSTRAINT ck_job_listing_work_mode        TO ck_jobs_work_mode;
ALTER TABLE jobs RENAME CONSTRAINT ck_job_listing_salary_period    TO ck_jobs_salary_period;
ALTER TABLE jobs RENAME CONSTRAINT ck_job_listing_salary_range     TO ck_jobs_salary_range;

ALTER INDEX ix_job_listing_company_id RENAME TO ix_jobs_company_id;
ALTER INDEX ix_job_listing_category   RENAME TO ix_jobs_category;
ALTER INDEX ix_job_listing_status     RENAME TO ix_jobs_status;
ALTER INDEX ix_job_listing_country    RENAME TO ix_jobs_country;
ALTER INDEX ix_job_listing_city       RENAME TO ix_jobs_city;

COMMIT;
