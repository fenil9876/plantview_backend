"""Dynamic validation engine.

Turns a stage's FieldDef rows into a validator for an entry payload, coercing
each value to a JSON-safe form for JSONB storage and collecting field-level errors.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.core.enums import FieldDataType
from app.models.template import FieldDef


class _FieldError(Exception):
    pass


def _coerce_int(value: Any) -> int:
    if isinstance(value, bool):
        raise _FieldError("expected an integer, got a boolean")
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        raise _FieldError("expected an integer, got a fractional number")
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            raise _FieldError("not a valid integer")
    raise _FieldError("not a valid integer")


def _coerce_decimal(value: Any) -> float:
    if isinstance(value, bool):
        raise _FieldError("expected a number, got a boolean")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(Decimal(value.strip()))
        except (InvalidOperation, ValueError):
            raise _FieldError("not a valid number")
    raise _FieldError("not a valid number")


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str) and value.strip().lower() in ("true", "false"):
        return value.strip().lower() == "true"
    raise _FieldError("not a valid boolean")


def _coerce_date(value: Any) -> str:
    if isinstance(value, str):
        try:
            return date.fromisoformat(value.strip()).isoformat()
        except ValueError:
            raise _FieldError("not a valid date (expected YYYY-MM-DD)")
    raise _FieldError("not a valid date (expected YYYY-MM-DD)")


def _coerce_datetime(value: Any) -> str:
    if isinstance(value, str):
        raw = value.strip().replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(raw).isoformat()
        except ValueError:
            raise _FieldError("not a valid datetime (expected ISO 8601)")
    raise _FieldError("not a valid datetime (expected ISO 8601)")


def _coerce_string(value: Any) -> str:
    if isinstance(value, str):
        return value
    raise _FieldError("expected a string")


def _apply_numeric_rules(value: float | int, rules: dict) -> None:
    if "min" in rules and value < rules["min"]:
        raise _FieldError(f"must be >= {rules['min']}")
    if "max" in rules and value > rules["max"]:
        raise _FieldError(f"must be <= {rules['max']}")


def _apply_string_rules(value: str, rules: dict) -> None:
    if "min_length" in rules and len(value) < rules["min_length"]:
        raise _FieldError(f"must be at least {rules['min_length']} characters")
    if "max_length" in rules and len(value) > rules["max_length"]:
        raise _FieldError(f"must be at most {rules['max_length']} characters")
    if "regex" in rules:
        try:
            if not re.match(rules["regex"], value):
                raise _FieldError("does not match the required format")
        except re.error:
            pass  # ignore a malformed pattern rather than 500


def _coerce_value(field: FieldDef, value: Any) -> Any:
    dt = field.data_type
    rules = field.validation or {}

    if dt == FieldDataType.INT.value:
        v = _coerce_int(value)
        _apply_numeric_rules(v, rules)
        return v
    if dt == FieldDataType.DECIMAL.value:
        v = _coerce_decimal(value)
        _apply_numeric_rules(v, rules)
        return v
    if dt == FieldDataType.BOOL.value:
        return _coerce_bool(value)
    if dt == FieldDataType.DATE.value:
        return _coerce_date(value)
    if dt == FieldDataType.DATETIME.value:
        return _coerce_datetime(value)
    if dt == FieldDataType.ENUM.value:
        v = _coerce_string(value)
        if v not in (field.options or []):
            raise _FieldError(f"must be one of {field.options}")
        return v
    # default: string
    v = _coerce_string(value)
    _apply_string_rules(v, rules)
    return v


def validate_payload(
    fields: list[FieldDef], data: dict[str, Any] | None, *, scope: str
) -> tuple[dict[str, Any], list[dict]]:
    """Validate `data` against `fields`.

    Returns (cleaned_data, errors). `errors` is a list of
    {scope, field, error}; cleaned_data holds only the recognized, coerced values.
    """
    data = data or {}
    errors: list[dict] = []
    cleaned: dict[str, Any] = {}
    defs = {f.key: f for f in fields}

    for key in data:
        if key not in defs:
            errors.append({"scope": scope, "field": key, "error": "unknown field"})

    for field in fields:
        present = field.key in data and data[field.key] is not None
        if not present:
            if field.required:
                errors.append({"scope": scope, "field": field.key, "error": "required"})
            continue
        try:
            cleaned[field.key] = _coerce_value(field, data[field.key])
        except _FieldError as exc:
            errors.append({"scope": scope, "field": field.key, "error": str(exc)})

    return cleaned, errors
