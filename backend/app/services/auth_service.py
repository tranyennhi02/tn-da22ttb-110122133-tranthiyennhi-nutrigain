from __future__ import annotations

import re

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models.entities import User
from app.repositories.user_repository import UserRepository
from app.views.schemas import AuthTokenResponse, UserCreate, UserLogin, UserView


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AuthService:
    @staticmethod
    def _validate_email(email: str) -> str:
        normalized = str(email or "").strip().lower()
        if not EMAIL_RE.match(normalized):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid email")
        return normalized

    @staticmethod
    def _validate_password(password: str) -> None:
        if len(password or "") < 8:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Password must contain at least 8 characters",
            )

    @staticmethod
    def _user_payload(user: User) -> UserView:
        return UserView(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at.isoformat(timespec="seconds"),
        )

    @classmethod
    def _token_payload(cls, user: User) -> AuthTokenResponse:
        token = create_access_token(
            subject=str(user.id),
            extra_claims={"email": user.email, "role": user.role},
        )
        return AuthTokenResponse(access_token=token, token_type="bearer", user=cls._user_payload(user))

    def register(self, payload: UserCreate, db: Session) -> AuthTokenResponse:
        email = self._validate_email(payload.email)
        self._validate_password(payload.password)

        repository = UserRepository(db)
        if repository.get_by_email(email) is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")

        try:
            role = "admin" if repository.count_users() == 0 else "user"
            user = repository.create_user(
                email=email,
                password_hash=hash_password(payload.password),
                full_name=payload.full_name,
                role=role,
            )
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists") from exc

        return self._token_payload(user)

    def login(self, payload: UserLogin, db: Session) -> AuthTokenResponse:
        email = self._validate_email(payload.email)
        user = UserRepository(db).get_by_email(email)
        if user is None or not verify_password(payload.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")
        return self._token_payload(user)
