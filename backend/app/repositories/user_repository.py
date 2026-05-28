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

    def get_by_google_sub(self, google_sub: str) -> User | None:
        query = select(User).where(User.google_sub == str(google_sub or "").strip())
        return self.db.scalar(query)

    def list_local_google_users(self) -> list[User]:
        query = select(User).where(
            func.lower(User.auth_provider) == "google",
            User.email.ilike("%@nutrigain.local"),
        )
        return list(self.db.scalars(query))

    def create_user(
        self,
        email: str,
        password_hash: str,
        full_name: str | None = None,
        role: str = "USER",
        auth_provider: str = "email",
        google_sub: str | None = None,
        email_verified: bool = False,
    ) -> User:
        user = User(
            email=email.strip().lower(),
            password_hash=password_hash,
            full_name=full_name,
            role=role,
            auth_provider=auth_provider,
            google_sub=google_sub,
            email_verified=email_verified,
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
        import inspect
        try:
            caller_frame = inspect.stack()[1]
            caller_filename = caller_frame.filename.split("\\")[-1].split("/")[-1]
            caller_function = caller_frame.function
            source_name = f"{caller_filename}:{caller_function}"
        except Exception:
            source_name = "unknown"
        print(f"[PROFILE WRITE SOURCE] {source_name} values={values}")

        profile = self.db.scalar(
            select(UserProfileEntity).where(UserProfileEntity.user_id == user_id)
        )
        if profile is None:
            profile = UserProfileEntity(user_id=user_id)
            self.db.add(profile)
            self.db.flush()
        for key, value in values.items():
            if hasattr(profile, key):
                # Logging writes for debugging disappearance/restore of disliked_foods
                if key == "disliked_foods" or key == "favorite_foods":
                    try:
                        old = getattr(profile, key, None)
                    except Exception:
                        old = None
                    print("[PROFILE WRITE SOURCE] user_repository.upsert_profile key=", key, "old=", old, "new=", value)
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
        return int(
            self.db.scalar(
                select(func.count(User.id)).where(func.upper(User.role).in_(["ADMIN", "SUPER_ADMIN"]))
            )
            or 0
        )
