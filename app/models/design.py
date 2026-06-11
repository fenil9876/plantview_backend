"""Design catalog: colors and designs (each design has an individual color)."""
from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin


class Color(TimestampMixin, Base):
    __tablename__ = "colors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    hex: Mapped[str | None] = mapped_column(String(9))  # e.g. #RRGGBB


class Design(TimestampMixin, Base):
    """Designs and colors are independent; an entry picks any design + any color."""
    __tablename__ = "designs"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
