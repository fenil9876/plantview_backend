"""Analytics response schemas."""
from datetime import datetime

from pydantic import BaseModel


class Overview(BaseModel):
    templates_total: int
    templates_active: int
    machines_total: int
    machines_active: int
    batches_total: int
    batches_by_status: dict[str, int]
    stage_entries_total: int
    machine_entries_total: int


class CountByStatus(BaseModel):
    status: str
    count: int


class CountByTemplate(BaseModel):
    template_id: int
    template_name: str
    count: int


class TimeseriesPoint(BaseModel):
    period: datetime
    count: int


class StageDistribution(BaseModel):
    stage_id: int
    stage_name: str
    order_index: int
    count: int


class MachineActivity(BaseModel):
    machine_id: int
    machine_name: str
    code: str
    entries: int
    batches: int


class FieldAggregateGroup(BaseModel):
    group_id: int
    group_label: str
    value: float | None
    count: int


class FieldAggregateResult(BaseModel):
    scope: str
    field: str
    op: str
    value: float | None = None          # populated when not grouped
    groups: list[FieldAggregateGroup] = []  # populated when group_by=machine


class MachineIO(BaseModel):
    machine_id: int
    machine_name: str
    input_total: float
    output_total: float
    wastage: float
    yield_pct: float | None
    entries: int
