"""Analytics queries.

Two kinds: structural metrics (independent of the dynamic field keys) and a
generic JSONB field-aggregation primitive that takes the field key + op as input.
"""
from typing import Any

from sqlalchemy import Float, and_, cast, func, or_, select
from sqlalchemy.orm import Session

from app.core.enums import FieldScope
from app.models.machine import Machine
from app.models.operations import Batch, MachineEntry, StageEntry
from app.models.template import Stage, Template
from app.services.exceptions import BadRequest

_AGG_OPS = {
    "sum": func.sum,
    "avg": func.avg,
    "min": func.min,
    "max": func.max,
}
ALLOWED_OPS = set(_AGG_OPS) | {"count"}
_INTERVALS = {"day", "week", "month"}

# Soft-deleted batches must not show up in any metric, otherwise the dashboard
# disagrees with the batch list. Every query below filters on this.
_LIVE_BATCH = Batch.deleted_at.is_(None)


def _f(v: Any) -> float | None:
    return float(v) if v is not None else None


# --------------------------------------------------------------------------- #
# Structural metrics
# --------------------------------------------------------------------------- #
def overview(db: Session) -> dict:
    by_status = dict(
        db.execute(
            select(Batch.status, func.count()).where(_LIVE_BATCH).group_by(Batch.status)
        ).all()
    )
    return {
        "templates_total": db.scalar(select(func.count()).select_from(Template)),
        "templates_active": db.scalar(
            select(func.count()).select_from(Template).where(Template.is_active.is_(True))
        ),
        "machines_total": db.scalar(select(func.count()).select_from(Machine)),
        "machines_active": db.scalar(
            select(func.count()).select_from(Machine).where(Machine.is_active.is_(True))
        ),
        "batches_total": db.scalar(select(func.count()).select_from(Batch).where(_LIVE_BATCH)),
        "batches_by_status": by_status,
        "stage_entries_total": db.scalar(
            select(func.count())
            .select_from(StageEntry)
            .join(Batch, Batch.id == StageEntry.batch_id)
            .where(_LIVE_BATCH)
        ),
        "machine_entries_total": db.scalar(
            select(func.count())
            .select_from(MachineEntry)
            .join(StageEntry, StageEntry.id == MachineEntry.stage_entry_id)
            .join(Batch, Batch.id == StageEntry.batch_id)
            .where(_LIVE_BATCH)
        ),
    }


def batches_by_status(db: Session) -> list[dict]:
    rows = db.execute(
        select(Batch.status, func.count())
        .where(_LIVE_BATCH)
        .group_by(Batch.status)
        .order_by(Batch.status)
    ).all()
    return [{"status": s, "count": n} for s, n in rows]


def batches_by_template(db: Session) -> list[dict]:
    rows = db.execute(
        select(Template.id, Template.name, func.count(Batch.id))
        .join(Batch, Batch.template_id == Template.id)
        .where(_LIVE_BATCH)
        .group_by(Template.id, Template.name)
        .order_by(func.count(Batch.id).desc())
    ).all()
    return [{"template_id": tid, "template_name": name, "count": n} for tid, name, n in rows]


def batches_timeseries(
    db: Session, *, interval: str = "day", template_id: int | None = None, status: str | None = None
) -> list[dict]:
    if interval not in _INTERVALS:
        raise BadRequest(f"interval must be one of {sorted(_INTERVALS)}")
    period = func.date_trunc(interval, Batch.created_at).label("period")
    stmt = select(period, func.count()).where(_LIVE_BATCH).group_by(period).order_by(period)
    if template_id is not None:
        stmt = stmt.where(Batch.template_id == template_id)
    if status is not None:
        stmt = stmt.where(Batch.status == status)
    return [{"period": p, "count": n} for p, n in db.execute(stmt).all()]


def batches_by_current_stage(db: Session, *, template_id: int) -> list[dict]:
    """Distribution of batches across a template's stages (all stages shown, incl. zero)."""
    counts = dict(
        db.execute(
            select(Batch.current_stage_id, func.count())
            .where(Batch.template_id == template_id, _LIVE_BATCH)
            .group_by(Batch.current_stage_id)
        ).all()
    )
    stages = db.scalars(
        select(Stage).where(Stage.template_id == template_id).order_by(Stage.order_index)
    ).all()
    return [
        {
            "stage_id": s.id,
            "stage_name": s.name,
            "order_index": s.order_index,
            "count": counts.get(s.id, 0),
        }
        for s in stages
    ]


def machine_activity(db: Session) -> list[dict]:
    rows = db.execute(
        select(
            Machine.id,
            Machine.name,
            Machine.code,
            func.count(MachineEntry.id),
            func.count(func.distinct(StageEntry.batch_id)),
        )
        .select_from(Machine)
        .outerjoin(MachineEntry, MachineEntry.machine_id == Machine.id)
        .outerjoin(StageEntry, StageEntry.id == MachineEntry.stage_entry_id)
        # Join only live batches, then drop the entries that failed to match.
        # Machines with no activity at all still survive and report zero.
        .outerjoin(Batch, and_(Batch.id == StageEntry.batch_id, _LIVE_BATCH))
        .where(or_(MachineEntry.id.is_(None), Batch.id.isnot(None)))
        .group_by(Machine.id, Machine.name, Machine.code)
        .order_by(func.count(MachineEntry.id).desc())
    ).all()
    return [
        {"machine_id": mid, "machine_name": name, "code": code, "entries": entries, "batches": batches}
        for mid, name, code, entries, batches in rows
    ]


# --------------------------------------------------------------------------- #
# Dynamic field aggregation (the JSONB primitive)
# --------------------------------------------------------------------------- #
def _scope_column(scope: FieldScope):
    if scope == FieldScope.STAGE:
        return StageEntry.data
    if scope == FieldScope.MACHINE_INPUT:
        return MachineEntry.input_data
    return MachineEntry.output_data


def field_aggregate(
    db: Session,
    *,
    scope: str,
    field: str,
    op: str,
    template_id: int | None = None,
    stage_id: int | None = None,
    machine_id: int | None = None,
    group_by: str | None = None,
) -> dict:
    op = op.lower()
    if op not in ALLOWED_OPS:
        raise BadRequest(f"op must be one of {sorted(ALLOWED_OPS)}")
    try:
        scope_enum = FieldScope(scope)
    except ValueError:
        raise BadRequest("scope must be one of stage, machine_input, machine_output")

    is_machine = scope_enum in (FieldScope.MACHINE_INPUT, FieldScope.MACHINE_OUTPUT)
    if group_by == "machine" and not is_machine:
        raise BadRequest("group_by=machine is only valid for machine_input/machine_output scopes")

    col = _scope_column(scope_enum)
    value = cast(col[field].astext, Float)
    is_number = func.jsonb_typeof(col[field]) == "number"
    measure = func.count() if op == "count" else _AGG_OPS[op](value)

    if not is_machine:
        # Always join Batch so soft-deleted batches are excluded.
        stmt = (
            select(measure)
            .select_from(StageEntry)
            .join(Batch, Batch.id == StageEntry.batch_id)
            .where(is_number, _LIVE_BATCH)
        )
        if stage_id is not None:
            stmt = stmt.where(StageEntry.stage_id == stage_id)
        if template_id is not None:
            stmt = stmt.where(Batch.template_id == template_id)
        return {"scope": scope, "field": field, "op": op, "value": _f(db.scalar(stmt)), "groups": []}

    # machine scope — the StageEntry/Batch join is now unconditional, since
    # excluding soft-deleted batches always requires reaching the batch.
    def _apply_machine_filters(stmt):
        stmt = stmt.join(StageEntry, StageEntry.id == MachineEntry.stage_entry_id).join(
            Batch, Batch.id == StageEntry.batch_id
        ).where(_LIVE_BATCH)
        if machine_id is not None:
            stmt = stmt.where(MachineEntry.machine_id == machine_id)
        if stage_id is not None:
            stmt = stmt.where(StageEntry.stage_id == stage_id)
        if template_id is not None:
            stmt = stmt.where(Batch.template_id == template_id)
        return stmt

    if group_by == "machine":
        stmt = select(
            MachineEntry.machine_id, Machine.name, measure, func.count()
        ).select_from(MachineEntry).join(Machine, Machine.id == MachineEntry.machine_id).where(is_number)
        stmt = _apply_machine_filters(stmt)
        stmt = stmt.group_by(MachineEntry.machine_id, Machine.name).order_by(MachineEntry.machine_id)
        groups = [
            {"group_id": mid, "group_label": name, "value": _f(val), "count": cnt}
            for mid, name, val, cnt in db.execute(stmt).all()
        ]
        return {"scope": scope, "field": field, "op": op, "value": None, "groups": groups}

    stmt = _apply_machine_filters(select(measure).select_from(MachineEntry).where(is_number))
    return {"scope": scope, "field": field, "op": op, "value": _f(db.scalar(stmt)), "groups": []}


def machine_io_summary(
    db: Session, *, input_field: str, output_field: str,
    stage_id: int | None = None, template_id: int | None = None,
) -> list[dict]:
    """Per-machine input/output totals, wastage and yield for two numeric fields."""
    inp = field_aggregate(
        db, scope=FieldScope.MACHINE_INPUT.value, field=input_field, op="sum",
        stage_id=stage_id, template_id=template_id, group_by="machine",
    )["groups"]
    out = field_aggregate(
        db, scope=FieldScope.MACHINE_OUTPUT.value, field=output_field, op="sum",
        stage_id=stage_id, template_id=template_id, group_by="machine",
    )["groups"]

    out_by_id = {g["group_id"]: g for g in out}
    result = []
    for g in inp:
        mid = g["group_id"]
        in_total = g["value"] or 0.0
        out_total = (out_by_id.get(mid, {}).get("value")) or 0.0
        wastage = in_total - out_total
        yield_pct = round(out_total / in_total * 100, 2) if in_total else None
        result.append({
            "machine_id": mid,
            "machine_name": g["group_label"],
            "input_total": in_total,
            "output_total": out_total,
            "wastage": wastage,
            "yield_pct": yield_pct,
            "entries": g["count"],
        })
    return result
