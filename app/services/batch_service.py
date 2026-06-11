"""Batch lifecycle + validated stage/machine data entry, with audit."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import AuditAction, BatchStatus, FieldScope
from app.models.design import Color, Design
from app.models.inventory import InventoryItem
from app.models.operations import (
    Batch,
    BatchColorTarget,
    BatchMaterial,
    MachineEntry,
    StageEntry,
)
from app.models.template import Stage, Template
from app.schemas.operations import (
    BatchColorTargetSubmit,
    BatchCreate,
    BatchMaterialSubmit,
    BatchUpdate,
    StageEntrySubmit,
)
from app.services import audit_service, template_service
from app.services.exceptions import BadRequest, Conflict, DataValidationError, Forbidden, NotFound
from app.services.field_validation import validate_payload


# --------------------------------------------------------------------------- #
# Batches
# --------------------------------------------------------------------------- #
def get_batch(db: Session, batch_id: int) -> Batch:
    batch = db.get(Batch, batch_id)
    if batch is None:
        raise NotFound(f"Batch {batch_id} not found")
    return batch


def list_batches(
    db: Session, *, template_id: int | None = None, status: str | None = None
) -> list[Batch]:
    stmt = select(Batch).order_by(Batch.created_at.desc(), Batch.id.desc())
    if template_id is not None:
        stmt = stmt.where(Batch.template_id == template_id)
    if status is not None:
        stmt = stmt.where(Batch.status == status)
    return list(db.scalars(stmt).all())


def create_batch(db: Session, payload: BatchCreate, actor_id: int | None) -> Batch:
    template = template_service.get_template(db, payload.template_id)
    if not template.is_active:
        raise BadRequest("Cannot create a batch on an inactive template")
    if db.scalar(select(Batch).where(Batch.code == payload.code)):
        raise Conflict(f"Batch code '{payload.code}' already exists")

    first_stage = template.stages[0] if template.stages else None
    batch = Batch(
        template_id=template.id,
        code=payload.code,
        lot_size=payload.lot_size,
        current_stage_id=first_stage.id if first_stage else None,
        status=BatchStatus.IN_PROGRESS.value,
        created_by=actor_id,
    )
    db.add(batch)
    db.flush()
    audit_service.record(
        db, entity_type="batch", entity_id=batch.id, action=AuditAction.CREATE,
        actor_id=actor_id, after={"code": batch.code, "template_id": batch.template_id},
    )
    if payload.materials:
        _apply_materials(db, batch, payload.materials, actor_id)
    db.commit()
    db.refresh(batch)
    return batch


# --------------------------------------------------------------------------- #
# Batch materials (inventory consumption)
# --------------------------------------------------------------------------- #
def _apply_materials(
    db: Session, batch: Batch, items: list[BatchMaterialSubmit], actor_id: int | None
) -> None:
    """Reconcile a batch's material consumption against main inventory (delta-based).

    Deducts increases and restores decreases/removals. Does NOT commit.
    """
    new_map: dict[int, float] = {}
    for it in items:
        if it.quantity <= 0:
            continue  # zero means "not used"
        if it.inventory_item_id in new_map:
            raise BadRequest(f"Duplicate material {it.inventory_item_id}")
        new_map[it.inventory_item_id] = it.quantity

    old_map = {bm.inventory_item_id: bm.quantity for bm in batch.materials}
    affected = set(new_map) | set(old_map)
    if not affected:
        return

    inv = {
        i.id: i
        for i in db.scalars(select(InventoryItem).where(InventoryItem.id.in_(affected))).all()
    }
    missing = set(new_map) - set(inv)
    if missing:
        raise BadRequest(f"Unknown inventory items: {sorted(missing)}")

    # Check stock for net increases before applying anything.
    shortages = []
    for iid in affected:
        delta = new_map.get(iid, 0.0) - old_map.get(iid, 0.0)
        if delta > 0 and inv[iid].quantity - delta < 0:
            shortages.append(f"{inv[iid].name} (need {delta}, have {inv[iid].quantity})")
    if shortages:
        raise BadRequest("Not enough stock: " + "; ".join(shortages))

    for iid in affected:
        delta = new_map.get(iid, 0.0) - old_map.get(iid, 0.0)
        if delta != 0:
            inv[iid].quantity -= delta

    batch.materials = [
        BatchMaterial(inventory_item_id=iid, quantity=q) for iid, q in new_map.items()
    ]
    audit_service.record(
        db, entity_type="batch", entity_id=batch.id, action=AuditAction.UPDATE,
        actor_id=actor_id,
        before={"materials": old_map},
        after={"materials": new_map},
    )


def set_batch_materials(
    db: Session, batch_id: int, items: list[BatchMaterialSubmit], actor_id: int | None
) -> Batch:
    batch = get_batch(db, batch_id)
    _apply_materials(db, batch, items, actor_id)
    db.commit()
    db.refresh(batch)
    return batch


def update_batch(db: Session, batch_id: int, payload: BatchUpdate, actor_id: int | None) -> Batch:
    """Update editable batch metadata (currently the lot size / target quantity)."""
    batch = get_batch(db, batch_id)
    data = payload.model_dump(exclude_unset=True)
    before = {k: getattr(batch, k) for k in data}
    for k, v in data.items():
        setattr(batch, k, v)
    if data:
        audit_service.record(
            db, entity_type="batch", entity_id=batch.id, action=AuditAction.UPDATE,
            actor_id=actor_id, before=before, after=data,
        )
    db.commit()
    db.refresh(batch)
    return batch


def set_batch_color_targets(
    db: Session, batch_id: int, targets: list[BatchColorTargetSubmit], actor_id: int | None
) -> Batch:
    """Set the planned per-color quantity split for a lot (replaces the existing set)."""
    batch = get_batch(db, batch_id)
    new_map: dict[int, float] = {}
    for t in targets:
        if t.quantity <= 0:
            continue  # zero means "not part of the split"
        if t.color_id in new_map:
            raise BadRequest(f"Duplicate color {t.color_id} in split")
        new_map[t.color_id] = t.quantity

    if new_map:
        found = set(db.scalars(select(Color.id).where(Color.id.in_(new_map))).all())
        missing = set(new_map) - found
        if missing:
            raise BadRequest(f"Unknown colors: {sorted(missing)}")

    before = {ct.color_id: ct.quantity for ct in batch.color_targets}
    batch.color_targets = [
        BatchColorTarget(color_id=cid, quantity=q) for cid, q in new_map.items()
    ]
    audit_service.record(
        db, entity_type="batch", entity_id=batch.id, action=AuditAction.UPDATE,
        actor_id=actor_id, before={"color_targets": before}, after={"color_targets": new_map},
    )
    db.commit()
    db.refresh(batch)
    return batch


def update_status(db: Session, batch_id: int, status: BatchStatus, actor_id: int | None) -> Batch:
    batch = get_batch(db, batch_id)
    before = batch.status
    batch.status = status.value
    audit_service.record(
        db, entity_type="batch", entity_id=batch.id, action=AuditAction.UPDATE,
        actor_id=actor_id, before={"status": before}, after={"status": batch.status},
    )
    db.commit()
    db.refresh(batch)
    return batch


def delete_batch(db: Session, batch_id: int, actor_id: int | None) -> None:
    batch = get_batch(db, batch_id)
    # Return any consumed materials to main inventory.
    if batch.materials:
        ids = [bm.inventory_item_id for bm in batch.materials]
        inv = {i.id: i for i in db.scalars(select(InventoryItem).where(InventoryItem.id.in_(ids))).all()}
        for bm in batch.materials:
            if bm.inventory_item_id in inv:
                inv[bm.inventory_item_id].quantity += bm.quantity
    audit_service.record(
        db, entity_type="batch", entity_id=batch.id, action=AuditAction.DELETE,
        actor_id=actor_id, before={"code": batch.code},
    )
    db.delete(batch)
    db.commit()


# --------------------------------------------------------------------------- #
# Stage data entry
# --------------------------------------------------------------------------- #
def _entry_snapshot(entry: StageEntry) -> dict:
    return {
        "data": entry.data,
        "status": entry.status,
        "design_id": entry.design_id,
        "color_id": entry.color_id,
        "machines": [
            {
                "machine_id": m.machine_id,
                "input_data": m.input_data,
                "output_data": m.output_data,
                "quantity": m.quantity,
                "description": m.description,
            }
            for m in entry.machine_entries
        ],
    }


def _fields_by_scope(stage: Stage, scope: FieldScope):
    return [f for f in stage.field_defs if f.scope == scope.value]


def _validate_design_color(db: Session, payload: StageEntrySubmit) -> None:
    if payload.design_id is not None and db.get(Design, payload.design_id) is None:
        raise BadRequest(f"Unknown design {payload.design_id}")
    if payload.color_id is not None and db.get(Color, payload.color_id) is None:
        raise BadRequest(f"Unknown color {payload.color_id}")


def _validate_payload_for_stage(stage: Stage, payload: StageEntrySubmit) -> tuple[dict, list[dict]]:
    """Validate a submit payload against a stage; returns (clean_data, clean_machines)."""
    errors: list[dict] = []
    clean_data, errs = validate_payload(
        _fields_by_scope(stage, FieldScope.STAGE), payload.data, scope="stage"
    )
    errors.extend(errs)

    clean_machines: list[dict] = []
    if payload.machines and not stage.has_machines:
        errors.append({"scope": "machines", "field": "machines",
                       "error": "this stage does not support machine entries"})
    elif stage.has_machines and payload.machines:
        input_fields = _fields_by_scope(stage, FieldScope.MACHINE_INPUT)
        output_fields = _fields_by_scope(stage, FieldScope.MACHINE_OUTPUT)
        assigned = set(stage.machine_ids)
        seen: set[int] = set()
        for me in payload.machines:
            tag = f"machine:{me.machine_id}"
            if me.machine_id in seen:
                errors.append({"scope": "machines", "field": tag, "error": "duplicate machine"})
                continue
            seen.add(me.machine_id)
            if me.machine_id not in assigned:
                errors.append({"scope": "machines", "field": tag,
                               "error": "machine is not assigned to this stage"})
                continue
            ci, e1 = validate_payload(input_fields, me.input_data, scope=f"{tag}.input")
            co, e2 = validate_payload(output_fields, me.output_data, scope=f"{tag}.output")
            errors.extend(e1)
            errors.extend(e2)
            desc = me.description.strip() if me.description else None
            clean_machines.append(
                {
                    "machine_id": me.machine_id,
                    "input_data": ci,
                    "output_data": co,
                    "quantity": me.quantity,
                    "description": desc or None,
                }
            )

    # Some stages require a design and a color on every entry.
    if stage.requires_design_color:
        if payload.design_id is None:
            errors.append({"scope": "entry", "field": "design", "error": "design is required"})
        if payload.color_id is None:
            errors.append({"scope": "entry", "field": "color", "error": "color is required"})
    # Machine stages require at least one machine with a quantity (description stays optional).
    if stage.has_machines and not clean_machines:
        errors.append({"scope": "machines", "field": "machines",
                       "error": "add at least one machine with a quantity"})

    if errors:
        raise DataValidationError(errors)
    return clean_data, clean_machines


def _apply_entry(entry: StageEntry, payload: StageEntrySubmit, clean_data: dict,
                 clean_machines: list[dict], actor_id: int | None) -> None:
    entry.data = clean_data
    entry.status = payload.status.value
    entry.design_id = payload.design_id
    entry.color_id = payload.color_id
    entry.submitted_by = actor_id
    entry.machine_entries = [
        MachineEntry(
            machine_id=m["machine_id"],
            input_data=m["input_data"],
            output_data=m["output_data"],
            quantity=m["quantity"],
            description=m["description"],
            operator_id=actor_id,
        )
        for m in clean_machines
    ]


def create_stage_entry(
    db: Session, batch_id: int, stage_id: int, payload: StageEntrySubmit, actor_id: int | None
) -> StageEntry:
    """Add a new entry for a stage (a stage may have many entries per batch)."""
    batch = get_batch(db, batch_id)
    stage = template_service.get_stage(db, batch.template_id, stage_id)
    _validate_design_color(db, payload)
    clean_data, clean_machines = _validate_payload_for_stage(stage, payload)

    entry = StageEntry(batch_id=batch_id, stage_id=stage_id)
    db.add(entry)
    _apply_entry(entry, payload, clean_data, clean_machines, actor_id)
    db.flush()

    _advance_current_stage(db, batch, stage)
    audit_service.record(
        db, entity_type="stage_entry", entity_id=entry.id, action=AuditAction.CREATE,
        actor_id=actor_id, after=_entry_snapshot(entry),
    )
    db.commit()
    db.refresh(entry)
    return entry


def update_stage_entry(
    db: Session, batch_id: int, entry_id: int, payload: StageEntrySubmit,
    actor_id: int | None, is_admin: bool,
) -> StageEntry:
    """Edit an existing entry. Only its creator or an admin may do so."""
    entry = db.get(StageEntry, entry_id)
    if entry is None or entry.batch_id != batch_id:
        raise NotFound(f"Entry {entry_id} not found in batch {batch_id}")
    if not is_admin and entry.submitted_by != actor_id:
        raise Forbidden("You can only edit entries you created")

    batch = get_batch(db, batch_id)
    stage = template_service.get_stage(db, batch.template_id, entry.stage_id)
    _validate_design_color(db, payload)
    clean_data, clean_machines = _validate_payload_for_stage(stage, payload)

    before = _entry_snapshot(entry)
    _apply_entry(entry, payload, clean_data, clean_machines, actor_id)
    db.flush()

    audit_service.record(
        db, entity_type="stage_entry", entity_id=entry.id, action=AuditAction.UPDATE,
        actor_id=actor_id, before=before, after=_entry_snapshot(entry),
    )
    db.commit()
    db.refresh(entry)
    return entry


def delete_stage_entry(
    db: Session, batch_id: int, entry_id: int, actor_id: int | None, is_admin: bool
) -> None:
    """Delete an entry. Only its creator or an admin may do so."""
    entry = db.get(StageEntry, entry_id)
    if entry is None or entry.batch_id != batch_id:
        raise NotFound(f"Entry {entry_id} not found in batch {batch_id}")
    if not is_admin and entry.submitted_by != actor_id:
        raise Forbidden("You can only delete entries you created")

    audit_service.record(
        db, entity_type="stage_entry", entity_id=entry.id, action=AuditAction.DELETE,
        actor_id=actor_id, before=_entry_snapshot(entry),
    )
    db.delete(entry)
    db.commit()


def _advance_current_stage(db: Session, batch: Batch, entered: Stage) -> None:
    current_order = -1
    if batch.current_stage_id is not None:
        current = db.get(Stage, batch.current_stage_id)
        if current is not None:
            current_order = current.order_index
    if entered.order_index >= current_order:
        batch.current_stage_id = entered.id
