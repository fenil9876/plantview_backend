"""Health / readiness endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    """Liveness: the app is up."""
    return {"status": "ok", "env": settings.APP_ENV}


@router.get("/health/db")
def health_db(db: Session = Depends(get_db)) -> dict:
    """Readiness: the database is reachable."""
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "reachable"}
