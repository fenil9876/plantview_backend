"""User request/response schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.roles import Role


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=8, max_length=128)
    roles: list[Role] = Field(default_factory=lambda: [Role.VIEWER])


class RolesUpdate(BaseModel):
    roles: list[Role] = Field(min_length=1)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    username: str
    is_active: bool
    roles: list[str]
    created_at: datetime

    @classmethod
    def from_user(cls, user) -> "UserRead":
        return cls(
            id=user.id,
            email=user.email,
            username=user.username,
            is_active=user.is_active,
            roles=user.role_names,
            created_at=user.created_at,
        )
