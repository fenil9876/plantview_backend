"""Inventory schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class InventoryItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    quantity: float = Field(default=0.0, ge=0)
    unit: str = Field(default="kg", max_length=20)


class InventoryItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    quantity: float | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, max_length=20)


class InventoryItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    quantity: float
    unit: str
    updated_at: datetime
