"""Template-builder models: Template -> Stage -> FieldDef."""
from __future__ import annotations

from typing import Any

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class Template(TimestampMixin, Base):
    __tablename__ = "templates"
    __table_args__ = (UniqueConstraint("name", "version", name="uq_templates_name_version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    stages: Mapped[list["Stage"]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="Stage.order_index",
        lazy="selectin",
    )


class Stage(TimestampMixin, Base):
    __tablename__ = "stages"
    __table_args__ = (UniqueConstraint("template_id", "name", name="uq_stages_template_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(
        ForeignKey("templates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    has_machines: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # When true, every entry on this stage must pick a design and a color.
    requires_design_color: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    template: Mapped["Template"] = relationship(back_populates="stages")
    field_defs: Mapped[list["FieldDef"]] = relationship(
        back_populates="stage",
        cascade="all, delete-orphan",
        order_by="FieldDef.order_index",
        lazy="selectin",
    )
    stage_machines: Mapped[list["StageMachine"]] = relationship(
        back_populates="stage",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def machine_ids(self) -> list[int]:
        return [sm.machine_id for sm in self.stage_machines]


class FieldDef(TimestampMixin, Base):
    __tablename__ = "field_defs"
    __table_args__ = (
        UniqueConstraint("stage_id", "scope", "key", name="uq_field_defs_stage_scope_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    stage_id: Mapped[int] = mapped_column(
        ForeignKey("stages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scope: Mapped[str] = mapped_column(String(20), nullable=False)       # FieldScope value
    key: Mapped[str] = mapped_column(String(63), nullable=False)         # JSON key in entry data
    label: Mapped[str] = mapped_column(String(150), nullable=False)
    data_type: Mapped[str] = mapped_column(String(20), nullable=False)   # FieldDataType value
    required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    options: Mapped[list[Any] | None] = mapped_column(JSONB)             # enum option list
    validation: Mapped[dict[str, Any] | None] = mapped_column(JSONB)     # min/max/regex/...
    unit: Mapped[str | None] = mapped_column(String(30))
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    stage: Mapped["Stage"] = relationship(back_populates="field_defs")


# Imported here so the relationship target resolves; defined in machine.py.
from app.models.machine import StageMachine  # noqa: E402,F401
