-- One Click Apply tables. Run this against the existing PostgreSQL database.
-- The application generates UUID values in Python, so no UUID extension is needed.

CREATE TABLE IF NOT EXISTS app_user (
    user_id UUID PRIMARY KEY,
    phone VARCHAR(20) NOT NULL UNIQUE,
    email VARCHAR(255) UNIQUE,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    skills TEXT[] NOT NULL DEFAULT '{}',
    cv_url VARCHAR(500),
    country VARCHAR(2),
    region VARCHAR(100),
    city VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_app_user_skills
    ON app_user USING GIN (skills);

CREATE TABLE IF NOT EXISTS application (
    application_id UUID PRIMARY KEY,
    job_id UUID NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
    seeker_id UUID NOT NULL REFERENCES app_user(user_id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'submitted'
        CONSTRAINT ck_application_status
        CHECK (status IN ('submitted', 'viewed', 'shortlisted', 'accepted', 'rejected', 'withdrawn')),
    cv_url VARCHAR(500) NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_application_job_seeker UNIQUE (job_id, seeker_id)
);

CREATE INDEX IF NOT EXISTS ix_application_seeker_id ON application(seeker_id);
CREATE INDEX IF NOT EXISTS ix_application_job_applied ON application(job_id, applied_at);
