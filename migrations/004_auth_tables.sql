-- Migration 004: users and Google sign-in (app_user, user_identity, refresh_token, company_member).
--
-- Only needed if your database already exists (it was created before this change).
-- On a fresh database, skip this; starting the app creates these tables.
--
-- Run with:  psql ghana_jobs -f migrations/004_auth_tables.sql

BEGIN;

-- ---------- company.verified_at -> timezone-aware (old values were stored as UTC) ----------
ALTER TABLE company
    ALTER COLUMN verified_at TYPE TIMESTAMPTZ USING verified_at AT TIME ZONE 'UTC';

-- ---------- app_user: a person who signs in ----------
CREATE TABLE app_user (
    user_id        UUID          PRIMARY KEY,
    email          VARCHAR(320)  NOT NULL UNIQUE,
    email_verified BOOLEAN       NOT NULL DEFAULT false,
    full_name      VARCHAR(200),
    phone          VARCHAR(30)   UNIQUE,
    avatar_url     VARCHAR(1000),
    created_at     TIMESTAMPTZ   NOT NULL DEFAULT now(),
    last_login_at  TIMESTAMPTZ,
    CONSTRAINT ck_app_user_email_lowercase CHECK (email = lower(email))
);

-- ---------- user_identity: one row per sign-in method (Google `sub`) ----------
CREATE TABLE user_identity (
    identity_id      UUID         PRIMARY KEY,
    user_id          UUID         NOT NULL REFERENCES app_user (user_id) ON DELETE CASCADE,
    provider         VARCHAR(20)  NOT NULL,
    provider_subject VARCHAR(255) NOT NULL,
    email            VARCHAR(320),
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT ck_user_identity_provider CHECK (provider IN ('google', 'dev')),
    CONSTRAINT uq_user_identity_provider_subject UNIQUE (provider, provider_subject)
);
CREATE INDEX ix_user_identity_user_id ON user_identity (user_id);

-- ---------- refresh_token: hashed long-lived session tokens ----------
CREATE TABLE refresh_token (
    token_id   UUID        PRIMARY KEY,
    user_id    UUID        NOT NULL REFERENCES app_user (user_id) ON DELETE CASCADE,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_refresh_token_user_id ON refresh_token (user_id);

-- ---------- company_member: which users can act for which company ----------
CREATE TABLE company_member (
    company_id UUID        NOT NULL REFERENCES company (company_id) ON DELETE CASCADE,
    user_id    UUID        NOT NULL REFERENCES app_user (user_id) ON DELETE CASCADE,
    role       VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (company_id, user_id),
    CONSTRAINT ck_company_member_role CHECK (role IN ('owner', 'admin', 'recruiter'))
);
CREATE INDEX ix_company_member_user_id ON company_member (user_id);

COMMIT;
