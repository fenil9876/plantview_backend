"""Audit log read schema."""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_type: str
    entity_id: int
    action: str
    actor_id: int | None
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    at: datetime
