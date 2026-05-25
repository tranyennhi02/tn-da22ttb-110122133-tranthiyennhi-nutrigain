from __future__ import annotations

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.entities import User


ADMIN_EMAIL = "admin@nutrigain.local"
ADMIN_PASSWORD = "Admin@123456"


def main() -> None:
    db = SessionLocal()
    try:
        admin = db.scalar(select(User).where(User.email == ADMIN_EMAIL.strip().lower()))
        if admin is None:
            admin = User(email=ADMIN_EMAIL)
            db.add(admin)

        admin.email = ADMIN_EMAIL.strip().lower()
        admin.role = "ADMIN"
        admin.status = "ACTIVE"
        admin.is_active = True
        admin.password_hash = hash_password(ADMIN_PASSWORD)

        db.commit()
        print("Admin password reset successfully.")
        print(f"Email: {ADMIN_EMAIL}")
        print(f"Password: {ADMIN_PASSWORD}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()