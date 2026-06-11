"""Audit log helpers. Records are written within the caller's transaction."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import AuditAction
from app.models.audit import AuditLog


def record(
    db: Session,
    *,
    entity_type: str,
    entity_id: int,
    action: AuditAction,
    actor_id: int | None,
    before: dict | None = None,
    after: dict | None = None,
) -> None:
    """Add an audit row to the session (does NOT commit)."""
    db.add(
        AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action.value,
            actor_id=actor_id,
            before=before,
            after=after,
        )
    )


def list_logs(
    db: Session,
    *,
    entity_type: str | None = None,
    entity_id: int | None = None,
    limit: int = 100,
) -> list[AuditLog]:
    stmt = select(AuditLog).order_by(AuditLog.at.desc(), AuditLog.id.desc())
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    stmt = stmt.limit(min(limit, 500))
    return list(db.scalars(stmt).all())
