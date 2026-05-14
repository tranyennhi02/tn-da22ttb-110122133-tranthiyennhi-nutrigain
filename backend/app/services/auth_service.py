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
            role=str(user.role or "USER").upper(),
            status=str(getattr(user, "status", None) or ("ACTIVE" if user.is_active else "LOCKED")).upper(),
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
            user = repository.create_user(
                email=email,
                password_hash=hash_password(payload.password),
                full_name=payload.full_name,
                role="USER",
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
        if not user.is_active or str(getattr(user, "status", "") or "").upper() == "LOCKED":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tài khoản đã bị khóa.")
        return self._token_payload(user)

    def google_login(self, id_token: str, db: Session) -> AuthTokenResponse:
        import urllib.request
        import json
        import secrets
        from app.core.config import settings

        print("[GOOGLE CLIENT ID BACKEND]", "loaded" if settings.google_client_id else "missing")

        if not id_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token Google không hợp lệ.",
            )

        url = f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "NutriGain-API"})
            with urllib.request.urlopen(req, timeout=10) as response:
                google_data = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            print("[GOOGLE AUTH] Failed to verify token via Google API:", exc)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token Google không hợp lệ.",
            ) from exc

        aud = google_data.get("aud")
        email = google_data.get("email")
        name = google_data.get("name") or google_data.get("given_name") or (email.split("@")[0] if email else "Google User")

        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token Google không hợp lệ.",
            )

        if settings.google_client_id and aud != settings.google_client_id:
            print(f"[GOOGLE AUTH] Client ID mismatch. Expected: {settings.google_client_id}, Got: {aud}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token Google không hợp lệ.",
            )

        repository = UserRepository(db)
        user = repository.get_by_email(email)

        if user is None:
            dummy_password = secrets.token_hex(16)
            password_hash = hash_password(dummy_password)
            
            try:
                user = repository.create_user(
                    email=email,
                    password_hash=password_hash,
                    full_name=name,
                    role="USER",
                    auth_provider="google",
                )
            except IntegrityError as exc:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email đã được đăng ký bằng phương thức khác.",
                ) from exc

        if not user.is_active or str(getattr(user, "status", "") or "").upper() == "LOCKED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tài khoản đã bị khóa.",
            )

        return self._token_payload(user)
