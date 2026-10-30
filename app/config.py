"""App settings, read once from environment variables / .env at import time."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _csv(name: str, default: str = "") -> tuple[str, ...]:
    raw = os.getenv(name, default)
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        raise RuntimeError(f"{name} must be a whole number, got {raw!r}")
    if value <= 0:
        raise RuntimeError(f"{name} must be greater than 0")
    return value


def _bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    google_client_ids: tuple[str, ...]
    jwt_secret: str
    jwt_algorithm: str
    access_token_minutes: int
    refresh_token_days: int
    cors_origins: tuple[str, ...]
    enable_dev_login: bool


def _load_settings() -> Settings:
    jwt_secret = os.getenv("JWT_SECRET", "").strip()
    if len(jwt_secret) < 32:
        raise RuntimeError(
            "JWT_SECRET is missing or shorter than 32 characters. Generate one with: "
            "python3 -c \"import secrets; print(secrets.token_urlsafe(48))\" and put it in .env"
        )

    algorithm = os.getenv("JWT_ALGORITHM", "HS256").strip()
    if algorithm not in {"HS256", "HS384", "HS512"}:
        raise RuntimeError("JWT_ALGORITHM must be HS256, HS384 or HS512")

    return Settings(
        google_client_ids=_csv("GOOGLE_CLIENT_IDS"),
        jwt_secret=jwt_secret,
        jwt_algorithm=algorithm,
        access_token_minutes=_int("ACCESS_TOKEN_MINUTES", 15),
        refresh_token_days=_int("REFRESH_TOKEN_DAYS", 30),
        cors_origins=_csv("CORS_ORIGINS", "http://localhost:5173"),
        enable_dev_login=_bool("ENABLE_DEV_LOGIN", False),
    )


settings = _load_settings()
