from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.entities import User, UserProfileEntity


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        query = select(User).where(User.email == email.strip().lower())
        return self.db.scalar(query)

    def create_user(
        self,
        email: str,
        password_hash: str,
        full_name: str | None = None,
        role: str = "user",
    ) -> User:
        user = User(
            email=email.strip().lower(),
            password_hash=password_hash,
            full_name=full_name,
            role=role,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_user(self, user: User, values: dict) -> User:
        for key, value in values.items():
            setattr(user, key, value)
        self.db.commit()
        self.db.refresh(user)
        return user

    def upsert_profile(self, user_id: int, values: dict) -> UserProfileEntity:
        profile = self.db.scalar(
            select(UserProfileEntity).where(UserProfileEntity.user_id == user_id)
        )
        if profile is None:
            profile = UserProfileEntity(user_id=user_id)
            self.db.add(profile)
            self.db.flush()
        for key, value in values.items():
            setattr(profile, key, value)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def list_users(self, limit: int, offset: int = 0) -> list[User]:
        query = select(User).order_by(User.created_at.desc()).offset(offset).limit(limit)
        return list(self.db.scalars(query))

    def count_users(self) -> int:
        return int(self.db.scalar(select(func.count(User.id))) or 0)

    def count_active_users(self) -> int:
        return int(
            self.db.scalar(select(func.count(User.id)).where(User.is_active.is_(True))) or 0
        )

    def count_admin_users(self) -> int:
        return int(self.db.scalar(select(func.count(User.id)).where(User.role == "admin")) or 0)
