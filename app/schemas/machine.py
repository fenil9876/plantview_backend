"""Machine master schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MachineCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    code: str = Field(min_length=1, max_length=50)
    type: str | None = Field(default=None, max_length=50)
    is_active: bool = True


class MachineUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    code: str | None = Field(default=None, min_length=1, max_length=50)
    type: str | None = Field(default=None, max_length=50)
    is_active: bool | None = None


class MachineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    type: str | None
    is_active: bool
    created_at: datetime
