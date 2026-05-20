from __future__ import annotations

import hashlib
import logging
import re
import secrets
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models.entities import PasswordResetToken, User
from app.repositories.user_repository import UserRepository
from app.views.schemas import AuthTokenResponse, ForgotPasswordInput, ResetPasswordInput, UserCreate, UserLogin, UserView


logger = logging.getLogger(__name__)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
FORGOT_PASSWORD_MESSAGE = "Nếu email tồn tại, hướng dẫn đặt lại mật khẩu đã được gửi."
RESET_PASSWORD_SUCCESS_MESSAGE = "Đặt lại mật khẩu thành công."
RESET_LINK_INVALID_MESSAGE = "Liên kết đặt lại mật khẩu không hợp lệ."
RESET_LINK_EXPIRED_MESSAGE = "Liên kết đặt lại mật khẩu đã hết hạn."
RESET_LINK_USED_MESSAGE = "Liên kết đặt lại mật khẩu đã được sử dụng."


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

    @staticmethod
    def _hash_reset_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _reset_url(token: str) -> str:
        frontend_url = settings.frontend_url.rstrip("/") or "http://localhost:5173"
        return f"{frontend_url}/reset-password?token={token}"

    @staticmethod
    def _smtp_configured() -> bool:
        return bool(settings.smtp_host and settings.smtp_from)

    def _send_reset_password_message(self, email: str, reset_url: str, token: str) -> None:
        if not self._smtp_configured():
            import os
            frontend_url = str(settings.frontend_url).lower()
            env = str(settings.app_env or str(os.getenv("ENVIRONMENT", "")) or str(os.getenv("ENV", ""))).lower()
            is_local_frontend = "localhost" in frontend_url or "127.0.0.1" in frontend_url
            is_dev_env = env in ("development", "local", "dev") or str(os.getenv("DEBUG", "")).lower() == "true"
            if is_local_frontend or is_dev_env:
                dev_reset_url = f"http://localhost:5173/reset-password?token={token}"
                logger.warning("DEV reset password link: %s", dev_reset_url)
            return

        try:
            message = EmailMessage()
            message["Subject"] = "Đặt lại mật khẩu NutriGain"
            message["From"] = settings.smtp_from
            message["To"] = email
            message.set_content(
                "Bạn vừa yêu cầu đặt lại mật khẩu NutriGain.\n\n"
                f"Mở liên kết sau để đặt mật khẩu mới: {reset_url}\n\n"
                "Nếu bạn không yêu cầu thao tác này, hãy bỏ qua email này."
            )
            port = settings.smtp_port or 587
            with smtplib.SMTP(settings.smtp_host, port, timeout=10) as smtp:
                if port == 587:
                    smtp.starttls()
                if settings.smtp_user and settings.smtp_password:
                    smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.send_message(message)
        except Exception as exc:
            logger.warning("Unable to send reset password email; request kept generic: %s", exc)

    def forgot_password(self, payload: ForgotPasswordInput, db: Session) -> dict[str, str]:
        email = self._validate_email(payload.email)
        user = UserRepository(db).get_by_email(email)
        if user is None:
            return {"message": FORGOT_PASSWORD_MESSAGE}

        now = datetime.utcnow()
        token = secrets.token_urlsafe(32)
        token_hash = self._hash_reset_token(token)
        expires_at = now + timedelta(minutes=max(1, settings.reset_password_token_expire_minutes))

        existing_tokens = db.scalars(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.used_at.is_(None),
            )
        )
        for reset_token in existing_tokens:
            reset_token.used_at = now

        db.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=expires_at,
            )
        )
        db.commit()
        self._send_reset_password_message(user.email, self._reset_url(token), token)
        return {"message": FORGOT_PASSWORD_MESSAGE}

    def reset_password(self, payload: ResetPasswordInput, db: Session) -> dict[str, str]:
        token = str(payload.token or "").strip()
        if not token:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=RESET_LINK_INVALID_MESSAGE)
        self._validate_password(payload.new_password)
        if payload.new_password != payload.confirm_password:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Mật khẩu xác nhận không khớp.",
            )

        token_hash = self._hash_reset_token(token)
        reset_token = db.scalar(
            select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
        )
        if reset_token is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=RESET_LINK_INVALID_MESSAGE)
        if reset_token.used_at is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=RESET_LINK_USED_MESSAGE)
        now = datetime.utcnow()
        if reset_token.expires_at < now:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=RESET_LINK_EXPIRED_MESSAGE)

        user = db.get(User, reset_token.user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=RESET_LINK_INVALID_MESSAGE)

        user.password_hash = hash_password(payload.new_password)
        reset_token.used_at = now
        db.commit()
        return {"message": RESET_PASSWORD_SUCCESS_MESSAGE}

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
