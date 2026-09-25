from fastapi import FastAPI

from app.database import Base, engine
from app.routers import jobs

# Creates tables if they don't already exist.
# (Fine for local dev; swap for Alembic migrations later.)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Job Matching Platform API")

app.include_router(jobs.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
