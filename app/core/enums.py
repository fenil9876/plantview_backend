"""Domain enums for the template builder."""
from enum import Enum


class FieldScope(str, Enum):
    """Where a field belongs within a stage."""
    STAGE = "stage"                    # general stage-level data
    MACHINE_INPUT = "machine_input"    # per-machine input column
    MACHINE_OUTPUT = "machine_output"  # per-machine output column


class FieldDataType(str, Enum):
    """Admin-selectable column data types."""
    STRING = "string"
    INT = "int"
    DECIMAL = "decimal"
    BOOL = "bool"
    DATE = "date"
    DATETIME = "datetime"
    ENUM = "enum"  # fixed option list (options stored on the field)


MACHINE_SCOPES = {FieldScope.MACHINE_INPUT, FieldScope.MACHINE_OUTPUT}


class BatchStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class EntryStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"


class AuditAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
