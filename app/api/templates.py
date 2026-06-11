"""Template-builder endpoints. Reads: any authenticated user. Writes: admin."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.core.roles import Role
from app.models.user import User
from app.schemas.template import (
    FieldDefCreate,
    FieldDefRead,
    FieldDefUpdate,
    StageCreate,
    StageMachinesSet,
    StageRead,
    StageUpdate,
    TemplateCreate,
    TemplateRead,
    TemplateSummary,
    TemplateUpdate,
)
from app.services import template_service

router = APIRouter(prefix="/templates", tags=["templates"])
admin_only = [Depends(require_roles(Role.ADMIN))]
authed = [Depends(get_current_user)]


# --------------------------- Templates ------------------------------------- #
@router.get("", response_model=list[TemplateSummary], dependencies=authed)
def list_templates(db: Session = Depends(get_db)):
    return template_service.list_templates(db)


@router.get("/{template_id}", response_model=TemplateRead, dependencies=authed)
def get_template(template_id: int, db: Session = Depends(get_db)):
    return template_service.get_template(db, template_id)


@router.post("", response_model=TemplateRead, status_code=status.HTTP_201_CREATED,
             dependencies=admin_only)
def create_template(
    payload: TemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return template_service.create_template(db, payload, created_by=current_user.id)


@router.patch("/{template_id}", response_model=TemplateRead, dependencies=admin_only)
def update_template(template_id: int, payload: TemplateUpdate, db: Session = Depends(get_db)):
    return template_service.update_template_meta(db, template_id, payload)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=admin_only)
def delete_template(template_id: int, db: Session = Depends(get_db)):
    template_service.delete_template(db, template_id)


# --------------------------- Stages ---------------------------------------- #
@router.post("/{template_id}/stages", response_model=StageRead,
             status_code=status.HTTP_201_CREATED, dependencies=admin_only)
def add_stage(template_id: int, payload: StageCreate, db: Session = Depends(get_db)):
    return template_service.add_stage(db, template_id, payload)


@router.patch("/{template_id}/stages/{stage_id}", response_model=StageRead, dependencies=admin_only)
def update_stage(template_id: int, stage_id: int, payload: StageUpdate,
                 db: Session = Depends(get_db)):
    return template_service.update_stage(db, template_id, stage_id, payload)


@router.delete("/{template_id}/stages/{stage_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=admin_only)
def delete_stage(template_id: int, stage_id: int, db: Session = Depends(get_db)):
    template_service.delete_stage(db, template_id, stage_id)


@router.put("/{template_id}/stages/{stage_id}/machines", response_model=StageRead,
            dependencies=admin_only)
def set_stage_machines(template_id: int, stage_id: int, payload: StageMachinesSet,
                       db: Session = Depends(get_db)):
    return template_service.set_stage_machines(db, template_id, stage_id, payload.machine_ids)


# --------------------------- Fields ---------------------------------------- #
@router.post("/{template_id}/stages/{stage_id}/fields", response_model=FieldDefRead,
             status_code=status.HTTP_201_CREATED, dependencies=admin_only)
def add_field(template_id: int, stage_id: int, payload: FieldDefCreate,
              db: Session = Depends(get_db)):
    return template_service.add_field(db, template_id, stage_id, payload)


@router.patch("/{template_id}/stages/{stage_id}/fields/{field_id}", response_model=FieldDefRead,
              dependencies=admin_only)
def update_field(template_id: int, stage_id: int, field_id: int, payload: FieldDefUpdate,
                 db: Session = Depends(get_db)):
    return template_service.update_field(db, template_id, stage_id, field_id, payload)


@router.delete("/{template_id}/stages/{stage_id}/fields/{field_id}",
               status_code=status.HTTP_204_NO_CONTENT, dependencies=admin_only)
def delete_field(template_id: int, stage_id: int, field_id: int, db: Session = Depends(get_db)):
    template_service.delete_field(db, template_id, stage_id, field_id)
