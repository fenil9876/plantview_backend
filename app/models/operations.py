"""Operational data models: a Batch flows through stages, accumulating entries."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import BatchStatus, EntryStatus
from app.models.mixins import TimestampMixin


class Batch(TimestampMixin, Base):
    __tablename__ = "batches"

    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(
        ForeignKey("templates.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    lot_size: Mapped[float | None] = mapped_column(Float, nullable=True)  # target total quantity
    current_stage_id: Mapped[int | None] = mapped_column(
        ForeignKey("stages.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), default=BatchStatus.IN_PROGRESS.value, nullable=False
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # Soft delete: rows are never removed, just hidden from every read path.
    # Consumed materials stay deducted from inventory, and the code stays reserved.
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    deleted_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    stage_entries: Mapped[list["StageEntry"]] = relationship(
        back_populates="batch",
        cascade="all, delete-orphan",
        order_by="StageEntry.id",
        lazy="selectin",
    )
    materials: Mapped[list["BatchMaterial"]] = relationship(
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    color_targets: Mapped[list["BatchColorTarget"]] = relationship(
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    designs: Mapped[list["BatchDesign"]] = relationship(
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class BatchMaterial(Base):
    """Inventory consumed by a batch (deducted from main stock). One row per (batch, item)."""
    __tablename__ = "batch_materials"

    batch_id: Mapped[int] = mapped_column(
        ForeignKey("batches.id", ondelete="CASCADE"), primary_key=True
    )
    inventory_item_id: Mapped[int] = mapped_column(
        ForeignKey("inventory_items.id", ondelete="RESTRICT"), primary_key=True
    )
    quantity: Mapped[float] = mapped_column(Float, nullable=False)

    item: Mapped["InventoryItem"] = relationship(lazy="joined")

    @property
    def name(self) -> str:
        return self.item.name

    @property
    def unit(self) -> str:
        return self.item.unit


class BatchColorTarget(Base):
    """Planned per-color quantity split for a lot (lot-level bifurcation). One row per (batch, color)."""
    __tablename__ = "batch_color_targets"

    batch_id: Mapped[int] = mapped_column(
        ForeignKey("batches.id", ondelete="CASCADE"), primary_key=True
    )
    color_id: Mapped[int] = mapped_column(
        ForeignKey("colors.id", ondelete="CASCADE"), primary_key=True
    )
    quantity: Mapped[float] = mapped_column(Float, nullable=False)

    color: Mapped["Color"] = relationship(lazy="joined")

    @property
    def name(self) -> str:
        return self.color.name

    @property
    def hex(self) -> str | None:
        return self.color.hex


class BatchDesign(Base):
    """Designs available to a lot. Purely a pick-list restriction for data entry —
    no quantity is planned per design. An empty set means "no restriction": every
    design stays selectable. One row per (batch, design)."""
    __tablename__ = "batch_designs"

    batch_id: Mapped[int] = mapped_column(
        ForeignKey("batches.id", ondelete="CASCADE"), primary_key=True
    )
    design_id: Mapped[int] = mapped_column(
        ForeignKey("designs.id", ondelete="CASCADE"), primary_key=True
    )

    design: Mapped["Design"] = relationship(lazy="joined")

    @property
    def name(self) -> str:
        return self.design.name

    @property
    def description(self) -> str | None:
        return self.design.description


class StageEntry(TimestampMixin, Base):
    __tablename__ = "stage_entries"
    # Multiple entries are allowed per (batch, stage).

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(
        ForeignKey("batches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stage_id: Mapped[int] = mapped_column(
        ForeignKey("stages.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default=EntryStatus.SUBMITTED.value, nullable=False
    )
    design_id: Mapped[int | None] = mapped_column(
        ForeignKey("designs.id", ondelete="SET NULL"), nullable=True
    )
    color_id: Mapped[int | None] = mapped_column(
        ForeignKey("colors.id", ondelete="SET NULL"), nullable=True
    )
    submitted_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    batch: Mapped["Batch"] = relationship(back_populates="stage_entries")
    submitter: Mapped["User | None"] = relationship(lazy="joined")
    design: Mapped["Design | None"] = relationship(lazy="joined")
    color: Mapped["Color | None"] = relationship(lazy="joined")
    machine_entries: Mapped[list["MachineEntry"]] = relationship(
        back_populates="stage_entry",
        cascade="all, delete-orphan",
        order_by="MachineEntry.id",
        lazy="selectin",
    )

    @property
    def submitted_by_name(self) -> str | None:
        return self.submitter.username if self.submitter else None

    @property
    def design_name(self) -> str | None:
        return self.design.name if self.design else None

    @property
    def color_name(self) -> str | None:
        return self.color.name if self.color else None

    @property
    def color_hex(self) -> str | None:
        return self.color.hex if self.color else None


class MachineEntry(TimestampMixin, Base):
    __tablename__ = "machine_entries"
    __table_args__ = (
        UniqueConstraint("stage_entry_id", "machine_id", name="uq_machine_entries_entry_machine"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    stage_entry_id: Mapped[int] = mapped_column(
        ForeignKey("stage_entries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    machine_id: Mapped[int] = mapped_column(
        ForeignKey("machines.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    input_data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    output_data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    quantity: Mapped[float | None] = mapped_column(Float, nullable=True)  # optional, built-in
    description: Mapped[str | None] = mapped_column(Text, nullable=True)  # optional, built-in
    operator_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    stage_entry: Mapped["StageEntry"] = relationship(back_populates="machine_entries")
