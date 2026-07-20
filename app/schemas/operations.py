"""Operational data schemas: batches, stage entries, machine entries."""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import BatchStatus, EntryStatus


# --------------------------- Machine entries ------------------------------- #
class MachineEntrySubmit(BaseModel):
    machine_id: int
    input_data: dict[str, Any] = Field(default_factory=dict)
    output_data: dict[str, Any] = Field(default_factory=dict)
    quantity: float | None = None
    description: str | None = None


class MachineEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    machine_id: int
    input_data: dict[str, Any]
    output_data: dict[str, Any]
    quantity: float | None
    description: str | None
    operator_id: int | None


# --------------------------- Stage entries --------------------------------- #
class StageEntrySubmit(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)
    machines: list[MachineEntrySubmit] = Field(default_factory=list)
    design_id: int | None = None
    color_id: int | None = None
    status: EntryStatus = EntryStatus.SUBMITTED


class StageEntriesBulkCreate(BaseModel):
    """Create several stage entries at once (e.g. one per colour) in a single transaction."""

    entries: list[StageEntrySubmit] = Field(min_length=1)


class StageEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    batch_id: int
    stage_id: int
    data: dict[str, Any]
    status: EntryStatus
    design_id: int | None
    design_name: str | None
    color_id: int | None
    color_name: str | None
    color_hex: str | None
    submitted_by: int | None
    submitted_by_name: str | None
    machine_entries: list[MachineEntryRead]
    updated_at: datetime


# --------------------------- Batch materials ------------------------------- #
class BatchMaterialSubmit(BaseModel):
    inventory_item_id: int
    quantity: float = Field(ge=0)


class BatchMaterialsSet(BaseModel):
    materials: list[BatchMaterialSubmit] = Field(default_factory=list)


class BatchMaterialRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    inventory_item_id: int
    name: str
    unit: str
    quantity: float


# --------------------------- Batch color split ----------------------------- #
class BatchColorTargetSubmit(BaseModel):
    color_id: int
    quantity: float = Field(ge=0)


class BatchColorTargetsSet(BaseModel):
    targets: list[BatchColorTargetSubmit] = Field(default_factory=list)


class BatchColorTargetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    color_id: int
    name: str
    hex: str | None
    quantity: float


# --------------------------- Batch designs --------------------------------- #
class BatchDesignsSet(BaseModel):
    """Designs a lot may use. Empty means no restriction (all designs selectable)."""

    design_ids: list[int] = Field(default_factory=list)


class BatchDesignRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    design_id: int
    name: str
    description: str | None


# --------------------------- Batches --------------------------------------- #
class BatchCreate(BaseModel):
    template_id: int
    code: str = Field(min_length=1, max_length=80)
    lot_size: float | None = Field(default=None, ge=0)
    materials: list[BatchMaterialSubmit] = Field(default_factory=list)


class BatchUpdate(BaseModel):
    lot_size: float | None = Field(default=None, ge=0)


class BatchStatusUpdate(BaseModel):
    status: BatchStatus


class BatchSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    template_id: int
    code: str
    lot_size: float | None
    current_stage_id: int | None
    status: BatchStatus
    created_by: int | None
    created_at: datetime


class BatchRead(BatchSummary):
    stage_entries: list[StageEntryRead]
    materials: list[BatchMaterialRead]
    color_targets: list[BatchColorTargetRead]
    designs: list[BatchDesignRead]
