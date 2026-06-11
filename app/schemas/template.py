"""Template-builder schemas (templates, stages, field definitions)."""
import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.enums import MACHINE_SCOPES, FieldDataType, FieldScope

KEY_RE = re.compile(r"^[a-z][a-z0-9_]*$")


# --------------------------------------------------------------------------- #
# Field definitions
# --------------------------------------------------------------------------- #
class FieldDefBase(BaseModel):
    scope: FieldScope
    key: str = Field(min_length=1, max_length=63)
    label: str = Field(min_length=1, max_length=150)
    data_type: FieldDataType
    required: bool = False
    options: list[Any] | None = None
    validation: dict[str, Any] | None = None
    unit: str | None = Field(default=None, max_length=30)
    order_index: int = 0

    @field_validator("key")
    @classmethod
    def _valid_key(cls, v: str) -> str:
        if not KEY_RE.match(v):
            raise ValueError(
                "key must be snake_case: start with a letter, then lowercase letters, digits or underscores"
            )
        return v

    @model_validator(mode="after")
    def _enum_needs_options(self):
        if self.data_type == FieldDataType.ENUM and not self.options:
            raise ValueError("data_type 'enum' requires a non-empty 'options' list")
        if self.data_type != FieldDataType.ENUM and self.options:
            raise ValueError("'options' is only allowed when data_type is 'enum'")
        return self


class FieldDefCreate(FieldDefBase):
    pass


class FieldDefUpdate(BaseModel):
    """Safe-to-change attributes only; key/scope/data_type are immutable to protect stored data."""
    label: str | None = Field(default=None, min_length=1, max_length=150)
    required: bool | None = None
    options: list[Any] | None = None
    validation: dict[str, Any] | None = None
    unit: str | None = Field(default=None, max_length=30)
    order_index: int | None = None


class FieldDefRead(FieldDefBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    stage_id: int


# --------------------------------------------------------------------------- #
# Stages
# --------------------------------------------------------------------------- #
class StageCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    order_index: int = 0
    has_machines: bool = False
    requires_design_color: bool = False
    fields: list[FieldDefCreate] = Field(default_factory=list)
    machine_ids: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_machine_consistency(self):
        has_machine_fields = any(f.scope in MACHINE_SCOPES for f in self.fields)
        if has_machine_fields and not self.has_machines:
            raise ValueError(
                "stage has machine_input/machine_output fields but has_machines is False"
            )
        if self.machine_ids and not self.has_machines:
            raise ValueError("machine_ids provided but has_machines is False")
        self._check_unique_keys(self.fields)
        return self

    @staticmethod
    def _check_unique_keys(fields: list[FieldDefCreate]) -> None:
        seen: set[tuple[str, str]] = set()
        for f in fields:
            sig = (f.scope.value, f.key)
            if sig in seen:
                raise ValueError(f"duplicate field key '{f.key}' within scope '{f.scope.value}'")
            seen.add(sig)


class StageUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    order_index: int | None = None
    has_machines: bool | None = None
    requires_design_color: bool | None = None


class StageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    template_id: int
    name: str
    order_index: int
    has_machines: bool
    requires_design_color: bool
    field_defs: list[FieldDefRead]
    machine_ids: list[int]


# --------------------------------------------------------------------------- #
# Templates
# --------------------------------------------------------------------------- #
class TemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = None
    version: int = Field(default=1, ge=1)
    stages: list[StageCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def _unique_stage_names(self):
        names = [s.name for s in self.stages]
        if len(names) != len(set(names)):
            raise ValueError("stage names must be unique within a template")
        return self


class TemplateUpdate(BaseModel):
    """Metadata only. Structural edits go through stage/field endpoints."""
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = None
    is_active: bool | None = None


class TemplateSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    version: int
    is_active: bool
    created_at: datetime


class TemplateRead(TemplateSummary):
    stages: list[StageRead]


# --------------------------------------------------------------------------- #
# Stage <-> machine assignment
# --------------------------------------------------------------------------- #
class StageMachinesSet(BaseModel):
    machine_ids: list[int] = Field(default_factory=list)
