"""Sign-in logic shared by POST /auth/google and POST /auth/dev-login."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models, schemas
from app.config import settings
from app.enums import AuthProvider
from app.security import create_access_token, hash_token, new_refresh_token


def normalize_email(email: str) -> str:
    return email.strip().lower()


def find_or_create_user(
    db: Session,
    *,
    provider: AuthProvider,
    subject: str,
    email: str,
    email_verified: bool,
    full_name: Optional[str],
    avatar_url: Optional[str],
) -> tuple[models.AppUser, bool]:
    """Return (user, is_new_user). Does not commit.

    1. Known sign-in (provider + subject) -> that user.
    2. Unknown sign-in, but a user already has this email -> link it, only if BOTH emails
       are verified (otherwise anyone could claim an account by its email address).
    3. Otherwise -> create the user and the identity.
    """
    email = normalize_email(email)

    identity = db.scalar(
        select(models.UserIdentity).where(
            models.UserIdentity.provider == provider,
            models.UserIdentity.provider_subject == subject,
        )
    )
    if identity is not None:
        user = identity.user
        identity.email = email
        if not user.full_name and full_name:
            user.full_name = full_name
        if avatar_url:
            user.avatar_url = avatar_url
        return user, False

    user = db.scalar(select(models.AppUser).where(models.AppUser.email == email))
    if user is not None:
        if not (user.email_verified and email_verified):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists and could not be linked",
            )
        db.add(
            models.UserIdentity(
                user=user, provider=provider, provider_subject=subject, email=email
            )
        )
        if not user.full_name and full_name:
            user.full_name = full_name
        if avatar_url and not user.avatar_url:
            user.avatar_url = avatar_url
        return user, False

    if not email_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email is not verified",
        )

    user = models.AppUser(
        email=email,
        email_verified=True,
        full_name=full_name,
        avatar_url=avatar_url,
    )
    db.add(user)
    db.add(
        models.UserIdentity(user=user, provider=provider, provider_subject=subject, email=email)
    )
    db.flush()  # surfaces unique-constraint races here instead of at commit
    return user, True


def accept_pending_invites(db: Session, user: models.AppUser) -> int:
    """Turn this user's pending company invites into memberships. Returns how many.

    Called by sign_in() on EVERY sign-in (Google and dev-login), after the user is found or
    created and before the response is built. So an invited person sees the company in
    `memberships` on their very first sign-in. Does not commit: sign_in() commits once for
    everything.
    """
    # -----------------------------------------------------------------------------------
    # TODO (T4.5). The CompanyInvite model (T4.3) and POST /companies/{id}/members (T4.4)
    # that creates invites are done; see app/models.py and app/routers/companies.py.
    #
    # 1. Find this user's invites that are still usable:
    #        now = datetime.now(timezone.utc)
    #        invites = db.scalars(
    #            select(models.CompanyInvite).where(
    #                models.CompanyInvite.email == user.email,   # both stored lowercase
    #                models.CompanyInvite.accepted_at.is_(None),  # not used yet
    #                models.CompanyInvite.expires_at > now,       # not expired
    #            )
    #        ).all()
    #
    # 2. For each invite:
    #      - If the user is NOT already a member of invite.company_id
    #        (db.get(models.CompanyMember, (invite.company_id, user.user_id)) is None),
    #        add models.CompanyMember(company_id=..., user_id=user.user_id, role=invite.role).
    #      - If they already are a member (e.g. added directly in the meantime), keep their
    #        current role. Don't add a second row: the primary key would reject it.
    #      - Either way, set invite.accepted_at = now so it is never used again.
    #
    # 3. Return the number of memberships you created.
    #
    # Why it's safe to match on email: sign_in() only runs for VERIFIED emails (Google
    # checks it; dev-login is local-only). Matching an unverified email would let anyone
    # join a company just by typing someone else's address.
    #
    # Done when:
    #   - owner invites new@example.com (T4.4), then dev-login as new@example.com
    #       -> the sign-in response's `memberships` already lists the company
    #       -> is_new_user is still true
    #       -> the invite row now has accepted_at set
    #   - signing in again does NOT create anything new (accepted invites are skipped)
    #   - an invite with expires_at in the past is ignored
    #     (test: UPDATE company_invite SET expires_at = now() - interval '1 day';)
    # -----------------------------------------------------------------------------------
    return 0


def get_memberships(db: Session, user_id: uuid.UUID) -> list[schemas.MembershipOut]:
    """Companies this user can act for, with their role in each."""
    rows = db.execute(
        select(models.CompanyMember, models.Company)
        .join(models.Company, models.Company.company_id == models.CompanyMember.company_id)
        .where(models.CompanyMember.user_id == user_id)
        .order_by(models.Company.name)
    ).all()
    return [
        schemas.MembershipOut(
            company_id=company.company_id,
            company_name=company.name,
            role=member.role,
            verified=company.verified,
        )
        for member, company in rows
    ]


def _issue_tokens(db: Session, user_id: uuid.UUID) -> tuple[str, str]:
    """Create an access token and store a new refresh token. Does not commit."""
    raw_refresh, refresh_hash = new_refresh_token()
    db.add(
        models.RefreshToken(
            user_id=user_id,
            token_hash=refresh_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_days),
        )
    )
    return create_access_token(user_id), raw_refresh


def sign_in(
    db: Session,
    *,
    provider: AuthProvider,
    subject: str,
    email: str,
    email_verified: bool,
    full_name: Optional[str],
    avatar_url: Optional[str],
) -> schemas.AuthResponse:
    """Find or create the user, record the login, and hand out tokens."""
    # Two first-time sign-ins for the same account at the same moment can both try to
    # insert; the loser hits a unique constraint, rolls back, and finds the winner's row.
    for attempt in range(2):
        try:
            user, is_new_user = find_or_create_user(
                db,
                provider=provider,
                subject=subject,
                email=email,
                email_verified=email_verified,
                full_name=full_name,
                avatar_url=avatar_url,
            )
            user.last_login_at = datetime.now(timezone.utc)
            accept_pending_invites(db, user)  # T4.5: does nothing until implemented
            access_token, refresh_token = _issue_tokens(db, user.user_id)
            db.commit()
            break
        except IntegrityError:
            db.rollback()
            if attempt == 1:
                raise

    db.refresh(user)
    return schemas.AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_minutes * 60,
        is_new_user=is_new_user,
        user=schemas.UserOut.from_model(user),
        memberships=get_memberships(db, user.user_id),
    )


def refresh_session(db: Session, raw_refresh_token: str) -> schemas.TokenResponse:
    """Swap a valid refresh token for a new access + refresh pair (the old one is revoked)."""
    now = datetime.now(timezone.utc)
    token = db.scalar(
        select(models.RefreshToken)
        .where(models.RefreshToken.token_hash == hash_token(raw_refresh_token))
        .with_for_update()
    )
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token is None:
        raise invalid

    if token.revoked_at is not None:
        # A revoked token being reused means it may have been stolen:
        # sign this user out everywhere.
        db.execute(
            update(models.RefreshToken)
            .where(
                models.RefreshToken.user_id == token.user_id,
                models.RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        db.commit()
        raise invalid

    if token.expires_at <= now:
        raise invalid

    token.revoked_at = now
    access_token, refresh_token = _issue_tokens(db, token.user_id)
    db.commit()
    return schemas.TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_minutes * 60,
    )


def revoke_refresh_token(db: Session, raw_refresh_token: str) -> None:
    """Log out one session. Silent if the token is unknown or already revoked."""
    db.execute(
        update(models.RefreshToken)
        .where(
            models.RefreshToken.token_hash == hash_token(raw_refresh_token),
            models.RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(timezone.utc))
    )
    db.commit()
