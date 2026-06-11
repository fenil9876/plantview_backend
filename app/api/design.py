"""Color and design endpoints. Reads: any authenticated user. Writes: admin or operator."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.core.roles import Role
from app.schemas.design import (
    ColorCreate,
    ColorRead,
    ColorUpdate,
    DesignCreate,
    DesignRead,
    DesignUpdate,
)
from app.services import design_service

writer = [Depends(require_roles(Role.ADMIN, Role.OPERATOR))]
reader = [Depends(get_current_user)]

color_router = APIRouter(prefix="/colors", tags=["colors"])
design_router = APIRouter(prefix="/designs", tags=["designs"])


# --------------------------- Colors --------------------------------------- #
@color_router.get("", response_model=list[ColorRead], dependencies=reader)
def list_colors(db: Session = Depends(get_db)):
    return design_service.list_colors(db)


@color_router.post("", response_model=ColorRead, status_code=status.HTTP_201_CREATED, dependencies=writer)
def create_color(payload: ColorCreate, db: Session = Depends(get_db)):
    return design_service.create_color(db, payload)


@color_router.patch("/{color_id}", response_model=ColorRead, dependencies=writer)
def update_color(color_id: int, payload: ColorUpdate, db: Session = Depends(get_db)):
    return design_service.update_color(db, color_id, payload)


@color_router.delete("/{color_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=writer)
def delete_color(color_id: int, db: Session = Depends(get_db)):
    design_service.delete_color(db, color_id)


# --------------------------- Designs -------------------------------------- #
@design_router.get("", response_model=list[DesignRead], dependencies=reader)
def list_designs(db: Session = Depends(get_db)):
    return design_service.list_designs(db)


@design_router.post("", response_model=DesignRead, status_code=status.HTTP_201_CREATED, dependencies=writer)
def create_design(payload: DesignCreate, db: Session = Depends(get_db)):
    return design_service.create_design(db, payload)


@design_router.patch("/{design_id}", response_model=DesignRead, dependencies=writer)
def update_design(design_id: int, payload: DesignUpdate, db: Session = Depends(get_db)):
    return design_service.update_design(db, design_id, payload)


@design_router.delete("/{design_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=writer)
def delete_design(design_id: int, db: Session = Depends(get_db)):
    design_service.delete_design(db, design_id)
