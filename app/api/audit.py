"""Audit log read endpoint (admin + viewer)."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.audit import AuditLogRead
from app.services import audit_service

router = APIRouter(prefix="/audit", tags=["audit"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[AuditLogRead])
def list_audit(
    entity_type: str | None = None,
    entity_id: int | None = None,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return audit_service.list_logs(
        db, entity_type=entity_type, entity_id=entity_id, limit=limit
    )
