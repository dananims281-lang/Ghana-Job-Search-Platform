-- Migration 005: company_invite table (pending invitations to join a company).
--
-- Only needed if your database already exists AND you haven't started the app since
-- pulling this change. Starting the app creates any missing table on its own, so if it
-- already ran, this file fails with "relation company_invite already exists". That's
-- harmless: the table is already there and identical.
--
-- Run with:  psql ghana_jobs -f migrations/005_company_invites.sql

BEGIN;

CREATE TABLE company_invite (
    invite_id   UUID         PRIMARY KEY,
    company_id  UUID         NOT NULL REFERENCES company (company_id) ON DELETE CASCADE,
    email       VARCHAR(320) NOT NULL,
    role        VARCHAR(20)  NOT NULL,
    invited_by  UUID         REFERENCES app_user (user_id) ON DELETE SET NULL,
    expires_at  TIMESTAMPTZ  NOT NULL,
    accepted_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT ck_company_invite_role CHECK (role IN ('owner', 'admin', 'recruiter')),
    CONSTRAINT ck_company_invite_email_lowercase CHECK (email = lower(email))
);
CREATE INDEX ix_company_invite_company_id ON company_invite (company_id);
CREATE INDEX ix_company_invite_email      ON company_invite (email);

COMMIT;
