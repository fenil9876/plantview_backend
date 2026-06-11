"""Machine master CRUD."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.machine import Machine
from app.schemas.machine import MachineCreate, MachineUpdate
from app.services.exceptions import Conflict, NotFound


def get(db: Session, machine_id: int) -> Machine:
    machine = db.get(Machine, machine_id)
    if machine is None:
        raise NotFound(f"Machine {machine_id} not found")
    return machine


def get_by_code(db: Session, code: str) -> Machine | None:
    return db.scalar(select(Machine).where(Machine.code == code))


def list_machines(db: Session, *, active_only: bool = False) -> list[Machine]:
    stmt = select(Machine).order_by(Machine.name)
    if active_only:
        stmt = stmt.where(Machine.is_active.is_(True))
    return list(db.scalars(stmt).all())


def create(db: Session, payload: MachineCreate) -> Machine:
    if get_by_code(db, payload.code):
        raise Conflict(f"Machine with code '{payload.code}' already exists")
    machine = Machine(**payload.model_dump())
    db.add(machine)
    db.commit()
    db.refresh(machine)
    return machine


def update(db: Session, machine_id: int, payload: MachineUpdate) -> Machine:
    machine = get(db, machine_id)
    data = payload.model_dump(exclude_unset=True)
    if "code" in data and data["code"] != machine.code:
        if get_by_code(db, data["code"]):
            raise Conflict(f"Machine with code '{data['code']}' already exists")
    for k, v in data.items():
        setattr(machine, k, v)
    db.commit()
    db.refresh(machine)
    return machine


def delete(db: Session, machine_id: int) -> None:
    machine = get(db, machine_id)
    db.delete(machine)
    db.commit()
