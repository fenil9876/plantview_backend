"""Inventory endpoints. Reads: any authenticated user. Writes: admin or operator."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.core.roles import Role
from app.schemas.inventory import InventoryItemCreate, InventoryItemRead, InventoryItemUpdate
from app.services import inventory_service

router = APIRouter(prefix="/inventory", tags=["inventory"])
writer = [Depends(require_roles(Role.ADMIN, Role.OPERATOR))]


@router.get("", response_model=list[InventoryItemRead], dependencies=[Depends(get_current_user)])
def list_items(db: Session = Depends(get_db)):
    return inventory_service.list_items(db)


@router.post("", response_model=InventoryItemRead, status_code=status.HTTP_201_CREATED, dependencies=writer)
def create_item(payload: InventoryItemCreate, db: Session = Depends(get_db)):
    return inventory_service.create(db, payload)


@router.patch("/{item_id}", response_model=InventoryItemRead, dependencies=writer)
def update_item(item_id: int, payload: InventoryItemUpdate, db: Session = Depends(get_db)):
    return inventory_service.update(db, item_id, payload)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=writer)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    inventory_service.delete(db, item_id)
