"""User management endpoints (admin only)."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.core.roles import Role
from app.models.user import User
from app.schemas.user import RolesUpdate, UserCreate, UserRead
from app.services import user_service

router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(require_roles(Role.ADMIN))],
)


@router.get("", response_model=list[UserRead])
def list_users(db: Session = Depends(get_db)) -> list[UserRead]:
    users = db.scalars(select(User).order_by(User.id)).all()
    return [UserRead.from_user(u) for u in users]


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db)) -> UserRead:
    if user_service.get_by_email(db, payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )
    user = user_service.create_user(
        db,
        email=payload.email,
        username=payload.username,
        password=payload.password,
        roles=payload.roles,
    )
    db.commit()
    db.refresh(user)
    return UserRead.from_user(user)


@router.put("/{user_id}/roles", response_model=UserRead)
def update_roles(
    user_id: int, payload: RolesUpdate, db: Session = Depends(get_db)
) -> UserRead:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user_service.set_roles(db, user, payload.roles)
    db.commit()
    db.refresh(user)
    return UserRead.from_user(user)
