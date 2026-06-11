"""Color and design schemas."""
import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def _validate_hex(v: str | None) -> str | None:
    if v in (None, ""):
        return None
    if not HEX_RE.match(v):
        raise ValueError("hex must look like #RRGGBB")
    return v.upper()


# --------------------------- Colors --------------------------------------- #
class ColorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    hex: str | None = None

    @field_validator("hex")
    @classmethod
    def _hex(cls, v):
        return _validate_hex(v)


class ColorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    hex: str | None = None

    @field_validator("hex")
    @classmethod
    def _hex(cls, v):
        return _validate_hex(v)


class ColorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    hex: str | None
    created_at: datetime


# --------------------------- Designs -------------------------------------- #
class DesignCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None


class DesignUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None


class DesignRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    created_at: datetime
