"""Template-builder business logic: templates, stages, fields, stage-machine links."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import MACHINE_SCOPES, FieldScope
from app.models.machine import Machine, StageMachine
from app.models.template import FieldDef, Stage, Template
from app.schemas.template import (
    FieldDefCreate,
    FieldDefUpdate,
    StageCreate,
    StageUpdate,
    TemplateCreate,
    TemplateUpdate,
)
from app.services.exceptions import BadRequest, Conflict, NotFound


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _validate_machine_ids(db: Session, machine_ids: list[int]) -> None:
    if not machine_ids:
        return
    unique = set(machine_ids)
    found = set(db.scalars(select(Machine.id).where(Machine.id.in_(unique))).all())
    missing = unique - found
    if missing:
        raise BadRequest(f"Unknown machine ids: {sorted(missing)}")


def _build_stage(db: Session, payload: StageCreate) -> Stage:
    stage = Stage(
        name=payload.name,
        order_index=payload.order_index,
        has_machines=payload.has_machines,
        requires_design_color=payload.requires_design_color,
    )
    for f in payload.fields:
        stage.field_defs.append(_build_field(f))
    _validate_machine_ids(db, payload.machine_ids)
    for mid in dict.fromkeys(payload.machine_ids):
        stage.stage_machines.append(StageMachine(machine_id=mid))
    return stage


def _build_field(payload: FieldDefCreate) -> FieldDef:
    return FieldDef(
        scope=payload.scope.value,
        key=payload.key,
        label=payload.label,
        data_type=payload.data_type.value,
        required=payload.required,
        options=payload.options,
        validation=payload.validation,
        unit=payload.unit,
        order_index=payload.order_index,
    )


# --------------------------------------------------------------------------- #
# Templates
# --------------------------------------------------------------------------- #
def get_template(db: Session, template_id: int) -> Template:
    template = db.get(Template, template_id)
    if template is None:
        raise NotFound(f"Template {template_id} not found")
    return template


def list_templates(db: Session) -> list[Template]:
    return list(db.scalars(select(Template).order_by(Template.name, Template.version)).all())


def create_template(db: Session, payload: TemplateCreate, created_by: int | None) -> Template:
    existing = db.scalar(
        select(Template).where(
            Template.name == payload.name, Template.version == payload.version
        )
    )
    if existing:
        raise Conflict(f"Template '{payload.name}' v{payload.version} already exists")

    template = Template(
        name=payload.name,
        description=payload.description,
        version=payload.version,
        created_by=created_by,
    )
    for s in payload.stages:
        template.stages.append(_build_stage(db, s))

    db.add(template)
    db.commit()
    db.refresh(template)
    return template


def update_template_meta(db: Session, template_id: int, payload: TemplateUpdate) -> Template:
    template = get_template(db, template_id)
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"] != template.name:
        clash = db.scalar(
            select(Template).where(
                Template.name == data["name"],
                Template.version == template.version,
                Template.id != template.id,
            )
        )
        if clash:
            raise Conflict(f"Template '{data['name']}' v{template.version} already exists")
    for k, v in data.items():
        setattr(template, k, v)
    db.commit()
    db.refresh(template)
    return template


def delete_template(db: Session, template_id: int) -> None:
    template = get_template(db, template_id)
    from app.models.operations import Batch  # local import to avoid a cycle
    if db.scalar(select(Batch.id).where(Batch.template_id == template_id).limit(1)):
        raise Conflict("Cannot delete a template that has batches; deactivate it instead")
    db.delete(template)
    db.commit()


# --------------------------------------------------------------------------- #
# Stages
# --------------------------------------------------------------------------- #
def get_stage(db: Session, template_id: int, stage_id: int) -> Stage:
    stage = db.get(Stage, stage_id)
    if stage is None or stage.template_id != template_id:
        raise NotFound(f"Stage {stage_id} not found in template {template_id}")
    return stage


def add_stage(db: Session, template_id: int, payload: StageCreate) -> Stage:
    template = get_template(db, template_id)
    if any(s.name == payload.name for s in template.stages):
        raise Conflict(f"Stage '{payload.name}' already exists in this template")
    stage = _build_stage(db, payload)
    template.stages.append(stage)
    db.commit()
    db.refresh(stage)
    return stage


def update_stage(db: Session, template_id: int, stage_id: int, payload: StageUpdate) -> Stage:
    stage = get_stage(db, template_id, stage_id)
    data = payload.model_dump(exclude_unset=True)

    if data.get("name") and data["name"] != stage.name:
        clash = db.scalar(
            select(Stage).where(
                Stage.template_id == template_id,
                Stage.name == data["name"],
                Stage.id != stage.id,
            )
        )
        if clash:
            raise Conflict(f"Stage '{data['name']}' already exists in this template")

    if data.get("has_machines") is False:
        # Refuse to disable machines while machine-scoped fields or links still exist.
        if any(f.scope in {s.value for s in MACHINE_SCOPES} for f in stage.field_defs):
            raise BadRequest("Cannot disable has_machines: machine fields still exist on this stage")
        if stage.stage_machines:
            raise BadRequest("Cannot disable has_machines: machines are still assigned to this stage")

    for k, v in data.items():
        setattr(stage, k, v)
    db.commit()
    db.refresh(stage)
    return stage


def delete_stage(db: Session, template_id: int, stage_id: int) -> None:
    stage = get_stage(db, template_id, stage_id)
    from app.models.operations import StageEntry  # local import to avoid a cycle
    if db.scalar(select(StageEntry.id).where(StageEntry.stage_id == stage_id).limit(1)):
        raise Conflict("Cannot delete a stage that has data entries")
    db.delete(stage)
    db.commit()


def set_stage_machines(db: Session, template_id: int, stage_id: int, machine_ids: list[int]) -> Stage:
    stage = get_stage(db, template_id, stage_id)
    if machine_ids and not stage.has_machines:
        raise BadRequest("Stage does not support machines (has_machines is False)")
    _validate_machine_ids(db, machine_ids)
    stage.stage_machines = [StageMachine(machine_id=mid) for mid in dict.fromkeys(machine_ids)]
    db.commit()
    db.refresh(stage)
    return stage


# --------------------------------------------------------------------------- #
# Fields
# --------------------------------------------------------------------------- #
def get_field(db: Session, template_id: int, stage_id: int, field_id: int) -> FieldDef:
    stage = get_stage(db, template_id, stage_id)
    field = db.get(FieldDef, field_id)
    if field is None or field.stage_id != stage.id:
        raise NotFound(f"Field {field_id} not found in stage {stage_id}")
    return field


def add_field(db: Session, template_id: int, stage_id: int, payload: FieldDefCreate) -> FieldDef:
    stage = get_stage(db, template_id, stage_id)
    if payload.scope in MACHINE_SCOPES and not stage.has_machines:
        raise BadRequest(
            f"Cannot add a {payload.scope.value} field: stage has_machines is False"
        )
    if any(f.scope == payload.scope.value and f.key == payload.key for f in stage.field_defs):
        raise Conflict(
            f"Field key '{payload.key}' already exists in scope '{payload.scope.value}'"
        )
    field = _build_field(payload)
    stage.field_defs.append(field)
    db.commit()
    db.refresh(field)
    return field


def update_field(
    db: Session, template_id: int, stage_id: int, field_id: int, payload: FieldDefUpdate
) -> FieldDef:
    field = get_field(db, template_id, stage_id, field_id)
    data = payload.model_dump(exclude_unset=True)
    # Guard the enum/options invariant against the (immutable) data_type.
    if "options" in data:
        from app.core.enums import FieldDataType
        if field.data_type == FieldDataType.ENUM.value and not data["options"]:
            raise BadRequest("enum field requires a non-empty options list")
        if field.data_type != FieldDataType.ENUM.value and data["options"]:
            raise BadRequest("options is only allowed for enum fields")
    for k, v in data.items():
        setattr(field, k, v)
    db.commit()
    db.refresh(field)
    return field


def delete_field(db: Session, template_id: int, stage_id: int, field_id: int) -> None:
    field = get_field(db, template_id, stage_id, field_id)
    db.delete(field)
    db.commit()
