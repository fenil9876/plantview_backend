"""User-related business logic, shared by the API and the seed script."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.roles import Role
from app.core.security import hash_password
from app.models.user import User, UserRole


def get_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def create_user(
    db: Session,
    *,
    email: str,
    username: str,
    password: str,
    roles: list[Role],
) -> User:
    """Create a user with the given roles. Caller handles uniqueness/commit policy."""
    user = User(
        email=email,
        username=username,
        password_hash=hash_password(password),
        is_active=True,
        roles=[UserRole(role=r.value) for r in dict.fromkeys(roles)],  # dedupe, keep order
    )
    db.add(user)
    db.flush()  # populate user.id without committing
    return user


def set_roles(db: Session, user: User, roles: list[Role]) -> User:
    user.roles = [UserRole(role=r.value) for r in dict.fromkeys(roles)]
    db.flush()
    return user


def set_password(db: Session, user: User, new_password: str) -> User:
    user.password_hash = hash_password(new_password)
    db.flush()
    return user
