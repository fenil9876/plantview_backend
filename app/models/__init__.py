"""Import all models here so Alembic autogenerate can discover them.

As models are added, import them in this module so they register on Base.metadata.
"""
from app.models.audit import AuditLog  # noqa: F401
from app.models.design import Color, Design  # noqa: F401
from app.models.inventory import InventoryItem  # noqa: F401
from app.models.machine import Machine, StageMachine  # noqa: F401
from app.models.operations import Batch, MachineEntry, StageEntry  # noqa: F401
from app.models.template import FieldDef, Stage, Template  # noqa: F401
from app.models.user import User, UserRole  # noqa: F401
