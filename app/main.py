import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import auth, companies, jobs, me

logger = logging.getLogger("uvicorn.error")

# Creates tables if they don't already exist.
# (Fine for local dev; swap for Alembic migrations later.)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Job Matching Platform API")

# Lets the browser frontend call the API. Tokens go in the Authorization header,
# not cookies, so credentials stay off.
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(me.router)
app.include_router(companies.router)
app.include_router(jobs.router)

if settings.enable_dev_login:
    from app.routers import dev_auth

    app.include_router(dev_auth.router)
    logger.warning(
        "ENABLE_DEV_LOGIN is on: POST /auth/dev-login lets anyone sign in as any email. "
        "Local development only; never enable it where real users can reach the API."
    )


@app.get("/health")
def health_check():
    return {"status": "ok"}
