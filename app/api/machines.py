"""Machine master endpoints. Reads: any authenticated user. Writes: admin."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.core.roles import Role
from app.schemas.machine import MachineCreate, MachineRead, MachineUpdate
from app.services import machine_service

router = APIRouter(prefix="/machines", tags=["machines"])
admin_only = [Depends(require_roles(Role.ADMIN))]


@router.get("", response_model=list[MachineRead], dependencies=[Depends(get_current_user)])
def list_machines(active_only: bool = False, db: Session = Depends(get_db)):
    return machine_service.list_machines(db, active_only=active_only)


@router.get("/{machine_id}", response_model=MachineRead, dependencies=[Depends(get_current_user)])
def get_machine(machine_id: int, db: Session = Depends(get_db)):
    return machine_service.get(db, machine_id)


@router.post("", response_model=MachineRead, status_code=status.HTTP_201_CREATED,
             dependencies=admin_only)
def create_machine(payload: MachineCreate, db: Session = Depends(get_db)):
    return machine_service.create(db, payload)


@router.patch("/{machine_id}", response_model=MachineRead, dependencies=admin_only)
def update_machine(machine_id: int, payload: MachineUpdate, db: Session = Depends(get_db)):
    return machine_service.update(db, machine_id, payload)


@router.delete("/{machine_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=admin_only)
def delete_machine(machine_id: int, db: Session = Depends(get_db)):
    machine_service.delete(db, machine_id)
