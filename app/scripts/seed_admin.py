"""Create the initial admin user.

Usage:
    python -m app.scripts.seed_admin

Reads FIRST_ADMIN_EMAIL / FIRST_ADMIN_PASSWORD from settings (.env).
Idempotent: if the user already exists, it is left unchanged.
"""
import sys

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.roles import Role
from app.services import user_service


def main() -> int:
    email = settings.FIRST_ADMIN_EMAIL
    password = settings.FIRST_ADMIN_PASSWORD
    if not email or not password:
        print("FIRST_ADMIN_EMAIL and FIRST_ADMIN_PASSWORD must be set in .env", file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        existing = user_service.get_by_email(db, email)
        if existing:
            print(f"Admin already exists: {email} (roles={existing.role_names})")
            return 0
        user = user_service.create_user(
            db, email=email, username="Admin", password=password, roles=[Role.ADMIN]
        )
        db.commit()
        print(f"Created admin: {email} (id={user.id})")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
