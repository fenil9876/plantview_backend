"""Batch + data-entry endpoints.

Reads: any authenticated user. Create/enter data: operator or admin. Delete: admin.
"""
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.core.enums import BatchStatus
from app.core.roles import Role
from app.models.user import User
from app.schemas.operations import (
    BatchCreate,
    BatchDesignsSet,
    BatchMaterialsSet,
    BatchRead,
    BatchStatusUpdate,
    BatchSummary,
    BatchUpdate,
    StageEntriesBulkCreate,
    StageEntryRead,
    StageEntrySubmit,
)
from app.services import batch_service

router = APIRouter(prefix="/batches", tags=["batches"])
authed = [Depends(get_current_user)]
operator_or_admin = [Depends(require_roles(Role.ADMIN, Role.OPERATOR))]
admin_only = [Depends(require_roles(Role.ADMIN))]


@router.get("", response_model=list[BatchSummary], dependencies=authed)
def list_batches(
    template_id: int | None = None,
    status: BatchStatus | None = None,
    search: str | None = Query(None, max_length=80, description="Case-insensitive batch code match"),
    db: Session = Depends(get_db),
):
    """List live batches. Soft-deleted batches are never returned."""
    return batch_service.list_batches(
        db, template_id=template_id, status=status.value if status else None, search=search
    )


@router.get("/{batch_id}", response_model=BatchRead, dependencies=authed)
def get_batch(batch_id: int, db: Session = Depends(get_db)):
    return batch_service.get_batch(db, batch_id)


@router.post("", response_model=BatchRead, status_code=status.HTTP_201_CREATED,
             dependencies=operator_or_admin)
def create_batch(
    payload: BatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return batch_service.create_batch(db, payload, actor_id=current_user.id)


@router.patch("/{batch_id}", response_model=BatchRead, dependencies=operator_or_admin)
def update_batch(
    batch_id: int,
    payload: BatchUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update batch metadata such as the lot size (target total quantity)."""
    return batch_service.update_batch(db, batch_id, payload, actor_id=current_user.id)


@router.put("/{batch_id}/materials", response_model=BatchRead, dependencies=operator_or_admin)
def set_batch_materials(
    batch_id: int,
    payload: BatchMaterialsSet,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Set the materials this batch consumes; reconciles the difference with main inventory."""
    return batch_service.set_batch_materials(db, batch_id, payload.materials, actor_id=current_user.id)


@router.put("/{batch_id}/designs", response_model=BatchRead, dependencies=operator_or_admin)
def set_batch_designs(
    batch_id: int,
    payload: BatchDesignsSet,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Set the designs this lot runs and the colours under each.

    Each design must be listed once and bring at least one colour. An empty list
    = no restriction (all designs and colours selectable during entry).
    """
    return batch_service.set_batch_designs(
        db, batch_id, payload.designs, actor_id=current_user.id
    )


@router.patch("/{batch_id}/status", response_model=BatchRead, dependencies=operator_or_admin)
def update_batch_status(
    batch_id: int,
    payload: BatchStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return batch_service.update_status(db, batch_id, payload.status, actor_id=current_user.id)


@router.delete("/{batch_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=admin_only)
def delete_batch(
    batch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft delete a batch: it disappears from all reads but no rows are removed."""
    batch_service.delete_batch(db, batch_id, actor_id=current_user.id)


@router.post("/{batch_id}/stages/{stage_id}/entries", response_model=StageEntryRead,
             status_code=status.HTTP_201_CREATED, dependencies=operator_or_admin)
def create_stage_entry(
    batch_id: int,
    stage_id: int,
    payload: StageEntrySubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a new entry for a stage (validated against field_defs). A stage may have many entries."""
    return batch_service.create_stage_entry(db, batch_id, stage_id, payload, actor_id=current_user.id)


@router.post("/{batch_id}/stages/{stage_id}/entries/bulk", response_model=list[StageEntryRead],
             status_code=status.HTTP_201_CREATED, dependencies=operator_or_admin)
def create_stage_entries_bulk(
    batch_id: int,
    stage_id: int,
    payload: StageEntriesBulkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add several entries for a stage in one atomic call (e.g. one per colour)."""
    return batch_service.create_stage_entries_bulk(
        db, batch_id, stage_id, payload.entries, actor_id=current_user.id
    )


@router.put("/{batch_id}/entries/{entry_id}", response_model=StageEntryRead,
            dependencies=operator_or_admin)
def update_stage_entry(
    batch_id: int,
    entry_id: int,
    payload: StageEntrySubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Edit an existing entry — allowed only for its creator or an admin."""
    return batch_service.update_stage_entry(
        db, batch_id, entry_id, payload,
        actor_id=current_user.id, is_admin="admin" in current_user.role_names,
    )


@router.delete("/{batch_id}/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=operator_or_admin)
def delete_stage_entry(
    batch_id: int,
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an entry — allowed only for its creator or an admin."""
    batch_service.delete_stage_entry(
        db, batch_id, entry_id,
        actor_id=current_user.id, is_admin="admin" in current_user.role_names,
    )
