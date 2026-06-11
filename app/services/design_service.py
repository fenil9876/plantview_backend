"""Color and design CRUD."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.design import Color, Design
from app.schemas.design import ColorCreate, ColorUpdate, DesignCreate, DesignUpdate
from app.services.exceptions import Conflict, NotFound


# --------------------------- Colors --------------------------------------- #
def list_colors(db: Session) -> list[Color]:
    return list(db.scalars(select(Color).order_by(Color.name)).all())


def get_color(db: Session, color_id: int) -> Color:
    color = db.get(Color, color_id)
    if color is None:
        raise NotFound(f"Color {color_id} not found")
    return color


def _color_by_name(db: Session, name: str) -> Color | None:
    return db.scalar(select(Color).where(Color.name == name))


def create_color(db: Session, payload: ColorCreate) -> Color:
    name = payload.name.strip()
    if _color_by_name(db, name):
        raise Conflict(f"Color '{name}' already exists")
    color = Color(name=name, hex=payload.hex)
    db.add(color)
    db.commit()
    db.refresh(color)
    return color


def update_color(db: Session, color_id: int, payload: ColorUpdate) -> Color:
    color = get_color(db, color_id)
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"]:
        new_name = data["name"].strip()
        if new_name != color.name and _color_by_name(db, new_name):
            raise Conflict(f"Color '{new_name}' already exists")
        color.name = new_name
    if "hex" in data:
        color.hex = data["hex"]
    db.commit()
    db.refresh(color)
    return color


def delete_color(db: Session, color_id: int) -> None:
    color = get_color(db, color_id)
    db.delete(color)
    db.commit()


# --------------------------- Designs -------------------------------------- #
def list_designs(db: Session) -> list[Design]:
    return list(db.scalars(select(Design).order_by(Design.name)).all())


def get_design(db: Session, design_id: int) -> Design:
    design = db.get(Design, design_id)
    if design is None:
        raise NotFound(f"Design {design_id} not found")
    return design


def _design_by_name(db: Session, name: str) -> Design | None:
    return db.scalar(select(Design).where(Design.name == name))


def create_design(db: Session, payload: DesignCreate) -> Design:
    name = payload.name.strip()
    if _design_by_name(db, name):
        raise Conflict(f"Design '{name}' already exists")
    design = Design(name=name, description=payload.description)
    db.add(design)
    db.commit()
    db.refresh(design)
    return design


def update_design(db: Session, design_id: int, payload: DesignUpdate) -> Design:
    design = get_design(db, design_id)
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"]:
        new_name = data["name"].strip()
        if new_name != design.name and _design_by_name(db, new_name):
            raise Conflict(f"Design '{new_name}' already exists")
        design.name = new_name
    if "description" in data:
        design.description = data["description"]
    db.commit()
    db.refresh(design)
    return design


def delete_design(db: Session, design_id: int) -> None:
    design = get_design(db, design_id)
    db.delete(design)
    db.commit()
