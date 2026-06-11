"""Inventory CRUD."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.inventory import InventoryItem
from app.schemas.inventory import InventoryItemCreate, InventoryItemUpdate
from app.services.exceptions import Conflict, NotFound


def get(db: Session, item_id: int) -> InventoryItem:
    item = db.get(InventoryItem, item_id)
    if item is None:
        raise NotFound(f"Inventory item {item_id} not found")
    return item


def get_by_name(db: Session, name: str) -> InventoryItem | None:
    return db.scalar(select(InventoryItem).where(InventoryItem.name == name))


def list_items(db: Session) -> list[InventoryItem]:
    return list(db.scalars(select(InventoryItem).order_by(InventoryItem.name)).all())


def create(db: Session, payload: InventoryItemCreate) -> InventoryItem:
    name = payload.name.strip()
    if get_by_name(db, name):
        raise Conflict(f"Inventory item '{name}' already exists")
    item = InventoryItem(name=name, quantity=payload.quantity, unit=payload.unit.strip() or "kg")
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update(db: Session, item_id: int, payload: InventoryItemUpdate) -> InventoryItem:
    item = get(db, item_id)
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"]:
        new_name = data["name"].strip()
        if new_name != item.name and get_by_name(db, new_name):
            raise Conflict(f"Inventory item '{new_name}' already exists")
        item.name = new_name
    if "quantity" in data and data["quantity"] is not None:
        item.quantity = data["quantity"]
    if "unit" in data and data["unit"]:
        item.unit = data["unit"].strip()
    db.commit()
    db.refresh(item)
    return item


def delete(db: Session, item_id: int) -> None:
    item = get(db, item_id)
    from app.models.operations import BatchMaterial  # local import to avoid a cycle
    if db.scalar(select(BatchMaterial.batch_id).where(BatchMaterial.inventory_item_id == item_id).limit(1)):
        raise Conflict("Cannot delete a material that is consumed by one or more batches")
    db.delete(item)
    db.commit()
