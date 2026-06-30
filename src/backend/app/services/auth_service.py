from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import re
import secrets
import smtplib
import time
from datetime import datetime, timedelta
from email.message import EmailMessage
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models.entities import EmailVerificationToken, PasswordResetToken, User
from app.repositories.user_repository import UserRepository
from app.services.email_service import send_verification_code_email
from app.views.schemas import (
    AuthTokenResponse,
    EmailVerificationInput,
    ForgotPasswordInput,
    MessageResponse,
    RegistrationVerificationResponse,
    ResendVerificationInput,
    ResetPasswordInput,
    UserCreate,
    UserLogin,
    UserView,
)


logger = logging.getLogger(__name__)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
FORGOT_PASSWORD_MESSAGE = "Nếu email tồn tại, hướng dẫn đặt lại mật khẩu đã được gửi."
RESET_PASSWORD_SUCCESS_MESSAGE = "Đặt lại mật khẩu thành công."
RESET_LINK_INVALID_MESSAGE = "Liên kết đặt lại mật khẩu không hợp lệ."
RESET_LINK_EXPIRED_MESSAGE = "Liên kết đặt lại mật khẩu đã hết hạn."
RESET_LINK_USED_MESSAGE = "Liên kết đặt lại mật khẩu đã được sử dụng."


def _is_local_email(email: str | None) -> bool:
    lowered = str(email or "").strip().lower()
    return lowered.endswith(".local") or "@nutrigain.local" in lowered


def _is_real_email(email: str | None) -> bool:
    normalized = str(email or "").strip().lower()
    return bool(EMAIL_RE.match(normalized)) and not _is_local_email(normalized)


def _normalize_google_sub(google_sub: str | None) -> str:
    return str(google_sub or "").strip()


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}".encode("ascii"))


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
            email_verified=bool(getattr(user, "email_verified", False)),
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
    def _hash_email_verification_code(code: str) -> str:
        return hashlib.sha256(code.encode("utf-8")).hexdigest()

    @staticmethod
    def _generate_verification_code() -> str:
        return f"{secrets.randbelow(1_000_000):06d}"

    @staticmethod
    def _normalize_verification_code(code: str) -> str:
        normalized = str(code or "").strip()
        if not normalized.isdigit() or len(normalized) != 6:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Mã xác thực không hợp lệ.")
        return normalized

    def _get_verification_token(self, db: Session, user: User) -> EmailVerificationToken | None:
        return db.scalar(
            select(EmailVerificationToken).where(
                EmailVerificationToken.user_id == user.id,
                EmailVerificationToken.consumed_at.is_(None),
            )
        )

    def _issue_verification_code(self, db: Session, user: User, *, enforce_rate_limit: bool = True) -> str:
        now = datetime.utcnow()
        token = self._get_verification_token(db, user)
        if token is None:
            token = EmailVerificationToken(
                user_id=user.id,
                code_hash="",
                expires_at=now,
                attempts=0,
                last_sent_at=now,
            )
            db.add(token)
            db.flush()
        elif enforce_rate_limit and (now - token.last_sent_at).total_seconds() < 60:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Vui lòng chờ 60 giây trước khi gửi lại mã.",
            )

        code = self._generate_verification_code()
        token.code_hash = self._hash_email_verification_code(code)
        token.expires_at = now + timedelta(minutes=10)
        token.attempts = 0
        token.last_sent_at = now
        token.consumed_at = None
        db.commit()
        db.refresh(token)
        
        # Actually send the email and check if it succeeded
        email_sent = send_verification_code_email(user.email, code)
        if not email_sent:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Không gửi được mã xác thực. Vui lòng thử lại sau hoặc kiểm tra cấu hình email.",
            )
        
        return code

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

    def register(self, payload: UserCreate, db: Session) -> RegistrationVerificationResponse:
        email = self._validate_email(payload.email)
        self._validate_password(payload.password)
        full_name = str(payload.full_name or "").strip()
        if not full_name:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Full name is required")

        repository = UserRepository(db)
        existing_user = repository.get_by_email(email)
        
        if existing_user is not None:
            email_verified = bool(getattr(existing_user, "email_verified", False))
            password_hash = getattr(existing_user, "password_hash", None)
            auth_provider = getattr(existing_user, "auth_provider", None)
            
            logger.info(
                "[REGISTER EXISTING USER STATE] email=%s email_verified=%s has_password_hash=%s auth_provider=%s",
                email[:3] + "***" if email else "<empty>",
                email_verified,
                bool(password_hash),
                auth_provider,
            )
            
            if email_verified:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email này đã có tài khoản. Vui lòng đăng nhập.",
                )
            
            # User exists but not verified - update password and resend verification
            existing_user.password_hash = hash_password(payload.password)
            existing_user.full_name = full_name
            existing_user.auth_provider = "email"
            existing_user.email_verified = False
            db.add(existing_user)
            db.commit()
            db.refresh(existing_user)
            user = existing_user
            
            # Send verification code
            try:
                logger.info("[EMAIL VERIFICATION SEND START] email=%s", email[:3] + "***" if email else "<empty>")
                self._issue_verification_code(db, user, enforce_rate_limit=False)
                logger.info("[EMAIL VERIFICATION SEND SUCCESS] email=%s", email[:3] + "***" if email else "<empty>")
            except HTTPException:
                raise
            except Exception:
                logger.exception("[EMAIL VERIFICATION SEND FAILED] email=%s", email[:3] + "***" if email else "<empty>")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Không gửi được mã xác thực. Vui lòng thử lại sau.",
                )
            
            return RegistrationVerificationResponse(
                requires_email_verification=True,
                email=user.email,
                message="Email này đã được đăng ký nhưng chưa xác thực. Mã xác thực mới đã được gửi.",
            )

        # New user registration
        try:
            user = repository.create_user(
                email=email,
                password_hash=hash_password(payload.password),
                full_name=full_name,
                role="USER",
                email_verified=False,
            )
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists") from exc

        # Send verification code
        try:
            logger.info("[EMAIL VERIFICATION SEND START] email=%s", email[:3] + "***" if email else "<empty>")
            self._issue_verification_code(db, user, enforce_rate_limit=False)
            logger.info("[EMAIL VERIFICATION SEND SUCCESS] email=%s", email[:3] + "***" if email else "<empty>")
        except HTTPException:
            raise
        except Exception:
            logger.exception("[EMAIL VERIFICATION SEND FAILED] email=%s", email[:3] + "***" if email else "<empty>")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Không gửi được mã xác thực. Vui lòng thử lại sau.",
            )
        
        return RegistrationVerificationResponse(
            requires_email_verification=True,
            email=user.email,
            message="Mã xác thực đã được gửi đến email của bạn.",
        )

    def login(self, payload: UserLogin, db: Session) -> AuthTokenResponse:
        email = self._validate_email(payload.email)
        user = UserRepository(db).get_by_email(email)
        
        if user is None:
            logger.info(
                "[LOGIN AUTH STATE] email=%s user_found=False",
                email[:3] + "***" if email else "<empty>",
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email hoặc mật khẩu không đúng.",
            )
        
        password_hash = getattr(user, "password_hash", None)
        email_verified = bool(getattr(user, "email_verified", False))
        auth_provider = getattr(user, "auth_provider", None)
        
        # Verify password first
        password_verified = False
        if password_hash:
            password_verified = verify_password(payload.password, password_hash)
        
        logger.info(
            "[LOGIN AUTH STATE] email=%s user_found=True has_password_hash=%s email_verified=%s auth_provider=%s password_verified=%s",
            email[:3] + "***" if email else "<empty>",
            bool(password_hash),
            email_verified,
            auth_provider,
            password_verified,
        )
        
        if not password_hash:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tài khoản này chưa có mật khẩu. Vui lòng đăng nhập bằng Google hoặc đặt lại mật khẩu.",
            )
        
        if not password_verified:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email hoặc mật khẩu không đúng.",
            )
        
        # Password is correct, now check email verification
        if not email_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email chưa được xác thực. Vui lòng nhập mã xác thực.",
            )
        
        if not user.is_active or str(getattr(user, "status", "") or "").upper() == "LOCKED":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tài khoản đã bị khóa.")
        
        return self._token_payload(user)

    def verify_email(self, payload: EmailVerificationInput, db: Session) -> AuthTokenResponse:
        email = self._validate_email(payload.email)
        code = self._normalize_verification_code(payload.code)
        user = UserRepository(db).get_by_email(email)
        if user is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mã xác thực chưa đúng.")
        if bool(getattr(user, "email_verified", False)):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email đã được xác thực.")

        token = self._get_verification_token(db, user)
        if token is None or token.consumed_at is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mã xác thực đã hết hạn.")

        now = datetime.utcnow()
        if token.expires_at < now or token.attempts >= 5:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mã xác thực đã hết hạn.")

        if token.code_hash != self._hash_email_verification_code(code):
            token.attempts += 1
            db.commit()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mã xác thực chưa đúng.")

        user.email_verified = True
        token.consumed_at = now
        db.add(user)
        db.add(token)
        db.commit()
        db.refresh(user)
        
        logger.info(
            "[EMAIL VERIFY SUCCESS] user_id=%s email=%s email_verified=%s",
            user.id,
            email[:3] + "***" if email else "<empty>",
            user.email_verified,
        )
        
        return self._token_payload(user)

    def resend_verification(self, payload: ResendVerificationInput, db: Session) -> MessageResponse:
        email = self._validate_email(payload.email)
        logger.info("[RESEND VERIFICATION START] email=%s", email[:3] + "***" if email else "<empty>")
        
        user = UserRepository(db).get_by_email(email)
        if user is None:
            logger.warning("[RESEND VERIFICATION] user_not_found email=%s", email[:3] + "***" if email else "<empty>")
            # Return generic message for security (don't reveal if email exists)
            return MessageResponse(message="Nếu email hợp lệ, mã xác thực đã được gửi.")
        
        email_verified = bool(getattr(user, "email_verified", False))
        
        if email_verified:
            logger.warning("[RESEND VERIFICATION] email_already_verified user_id=%s", user.id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email này đã được xác thực. Vui lòng đăng nhập.",
            )

        try:
            logger.info("[EMAIL VERIFICATION SEND START] user_id=%s", user.id)
            self._issue_verification_code(db, user, enforce_rate_limit=True)
            logger.info("[EMAIL VERIFICATION SEND SUCCESS] user_id=%s", user.id)
            return MessageResponse(message="Mã xác thực đã được gửi đến email của bạn.")
        except HTTPException:
            # Re-raise HTTP exceptions (rate limit, email send failure, etc.)
            raise
        except Exception:
            logger.exception("[EMAIL VERIFICATION SEND FAILED] user_id=%s", user.id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Không thể gửi mã xác thực. Vui lòng thử lại sau.",
            )

    @staticmethod
    def _google_state_ttl_seconds() -> int:
        return 600

    @staticmethod
    def _google_state_signing_key() -> bytes:
        return settings.jwt_secret_key.encode("utf-8")

    @classmethod
    def _build_google_oauth_state(cls, code_verifier: str) -> str:
        payload = {
            "nonce": secrets.token_urlsafe(16),
            "ts": int(time.time()),
            "verifier": code_verifier,
        }
        payload_raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        payload_encoded = _b64url_encode(payload_raw)
        signature = hmac.new(cls._google_state_signing_key(), payload_encoded.encode("ascii"), hashlib.sha256).digest()
        return f"{payload_encoded}.{_b64url_encode(signature)}"

    @classmethod
    def _parse_google_oauth_state(cls, state: str) -> dict[str, str]:
        logger.info("[GOOGLE OAUTH STATE VERIFY] ok=true reason=starting")
        try:
            payload_encoded, signature_encoded = state.split(".", 1)
        except ValueError as exc:
            logger.warning("[GOOGLE OAUTH STATE VERIFY] ok=false reason=missing_or_malformed")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Trạng thái Google không hợp lệ.") from exc

        expected_signature = hmac.new(
            cls._google_state_signing_key(),
            payload_encoded.encode("ascii"),
            hashlib.sha256,
        ).digest()

        try:
            provided_signature = _b64url_decode(signature_encoded)
        except Exception as exc:
            logger.warning("[GOOGLE OAUTH STATE VERIFY] ok=false reason=invalid_signature_encoding")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Trạng thái Google không hợp lệ.") from exc

        if not hmac.compare_digest(expected_signature, provided_signature):
            logger.warning("[GOOGLE OAUTH STATE VERIFY] ok=false reason=invalid_signature")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Trạng thái Google không hợp lệ.")

        try:
            payload = json.loads(_b64url_decode(payload_encoded).decode("utf-8"))
        except Exception as exc:
            logger.warning("[GOOGLE OAUTH STATE VERIFY] ok=false reason=invalid_payload")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Trạng thái Google không hợp lệ.") from exc

        ts = int(payload.get("ts") or 0)
        if not ts or (int(time.time()) - ts) > cls._google_state_ttl_seconds():
            logger.warning("[GOOGLE OAUTH STATE VERIFY] ok=false reason=expired")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Trạng thái Google đã hết hạn.")

        verifier = str(payload.get("verifier") or "").strip()
        if not verifier:
            logger.warning("[GOOGLE OAUTH STATE VERIFY] ok=false reason=missing_verifier")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Trạng thái Google không hợp lệ.")

        logger.info("[GOOGLE OAUTH STATE VERIFY] ok=true reason=valid")
        return {"verifier": verifier, "nonce": str(payload.get("nonce") or "")}

    @staticmethod
    def _pkce_challenge(code_verifier: str) -> str:
        digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
        return _b64url_encode(digest)

    def _exchange_google_code(self, code: str, code_verifier: str) -> dict:
        from app.core.config import settings as app_settings

        logger.info(
            "[GOOGLE OAUTH TOKEN EXCHANGE START] redirect_uri=%s secret_configured=%s",
            app_settings.google_redirect_uri,
            bool(app_settings.google_client_secret),
        )
        payload: dict[str, str] = {
            "code": code,
            "client_id": app_settings.google_client_id or "",
            "code_verifier": code_verifier,
            "grant_type": "authorization_code",
            "redirect_uri": app_settings.google_redirect_uri,
        }
        if app_settings.google_client_secret:
            payload["client_secret"] = app_settings.google_client_secret

        request = Request(
            "https://oauth2.googleapis.com/token",
            data=urlencode(payload).encode("utf-8"),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )

        try:
            with urlopen(request, timeout=15) as response:
                raw_body = response.read().decode("utf-8")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore") if getattr(exc, "read", None) else str(exc)
            logger.warning("[GOOGLE OAUTH TOKEN EXCHANGE FAILED] status=%s bodySafe=%s", getattr(exc, "code", None), str(detail)[:240])
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Không thể xác thực Google OAuth.") from exc
        except URLError as exc:
            logger.warning("[GOOGLE OAUTH TOKEN EXCHANGE FAILED] status=network bodySafe=%s", str(exc)[:240])
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Không thể kết nối tới Google.") from exc

        try:
            token_data = json.loads(raw_body)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Phản hồi Google OAuth không hợp lệ.") from exc

        if not isinstance(token_data, dict) or not token_data.get("id_token"):
            logger.warning("[GOOGLE OAUTH TOKEN EXCHANGE FAILED] status=200 bodySafe=%s", str(token_data)[:240])
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google OAuth không trả về id_token.")

        logger.info("[GOOGLE OAUTH TOKEN EXCHANGE SUCCESS] hasIdToken=%s", bool(token_data.get("id_token")))
        return token_data

    def _upsert_google_identity_user(self, google_data: dict, db: Session) -> AuthTokenResponse:
        email = str(google_data.get("email") or "").strip().lower()
        google_sub = _normalize_google_sub(google_data.get("sub"))
        name = google_data.get("name") or google_data.get("given_name") or (email.split("@")[0] if email else "Google User")
        email_verified = bool(google_data.get("email_verified"))

        if not _is_real_email(email):
            logger.warning("[GOOGLE OAUTH VERIFY ID TOKEN FAILED] error=invalid_email")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Google credential",
            )
        if not email_verified:
            logger.warning("[GOOGLE OAUTH VERIFY ID TOKEN FAILED] error=email_not_verified email=%s", email)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email Google chưa được xác thực.",
            )

        logger.info("[GOOGLE OAUTH VERIFY ID TOKEN SUCCESS] email=%s emailVerified=%s", email, email_verified)
        repository = UserRepository(db)
        logger.info("[GOOGLE OAUTH USER UPSERT START] email=%s", email)
        try:
            user = repository.get_by_google_sub(google_sub) if google_sub else None
            if user is None:
                user = repository.get_by_email(email)

            if user and str(user.email or "").strip().lower() == "admin@nutrigain.local" and email != "admin@nutrigain.local":
                user = None

            if user is None:
                logger.info("[GOOGLE OAUTH] Creating new user for email=%s", email)
                dummy_password = secrets.token_hex(16)
                password_hash = hash_password(dummy_password)
                user = repository.create_user(
                    email=email,
                    password_hash=password_hash,
                    full_name=name,
                    role="USER",
                    auth_provider="google",
                    google_sub=google_sub or None,
                    email_verified=True,
                )
                logger.info("[GOOGLE OAUTH] New user created: id=%s", user.id)
            else:
                logger.info("[GOOGLE OAUTH] Updating existing user: id=%s", user.id)
                user.auth_provider = "google"
                if google_sub:
                    user.google_sub = google_sub
                if user.email != email:
                    user.email = email
                if name:
                    user.full_name = name
                user.email_verified = True
                db.add(user)
                db.commit()
                db.refresh(user)
                logger.info("[GOOGLE OAUTH] User updated: id=%s", user.id)

            logger.info("[GOOGLE OAUTH USER UPSERT SUCCESS] userId=%s, profileComplete=%s", user.id, bool(getattr(user, "profile", None)))
        except IntegrityError as exc:
            db.rollback()
            logger.exception("[GOOGLE OAUTH USER UPSERT FAILED] IntegrityError - stacktrace:")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email đã được đăng ký bằng phương thức khác.",
            ) from exc
        except HTTPException:
            raise
        except Exception as exc:
            db.rollback()
            logger.exception("[GOOGLE OAUTH UNHANDLED ERROR] type=%s - stacktrace:", type(exc).__name__)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create/load user: {type(exc).__name__}",
            ) from exc

        logger.info("[GOOGLE OAUTH USER UPSERT] userId=%s, email=%s, profileComplete=%s", user.id, user.email, bool(getattr(user, "profile", None)))

        if not user.is_active or str(getattr(user, "status", "") or "").upper() == "LOCKED":
            logger.warning("[GOOGLE OAUTH] User account is locked: userId=%s", user.id)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tài khoản đã bị khóa.",
            )

        logger.info("[GOOGLE OAUTH] Generating token for userId=%s", user.id)
        response = self._token_payload(user)
        logger.info("[GOOGLE OAUTH RESPONSE] hasAccessToken=%s, hasUser=%s", bool(response.access_token), bool(response.user))
        return response

    def get_google_oauth_url(self) -> str:
        from app.core.config import settings as app_settings

        logger.info("[GOOGLE OAUTH URL START]")
        logger.info("[GOOGLE CLIENT SECRET CONFIGURED] %s", bool(app_settings.google_client_secret))
        logger.info("[GOOGLE REDIRECT URI] %s", app_settings.google_redirect_uri)
        if not app_settings.google_client_id:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Google OAuth is not configured on server.")

        code_verifier = secrets.token_urlsafe(64)
        state = self._build_google_oauth_state(code_verifier)
        query = urlencode({
            "client_id": app_settings.google_client_id,
            "redirect_uri": app_settings.google_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "select_account",
            "include_granted_scopes": "true",
            "code_challenge": self._pkce_challenge(code_verifier),
            "code_challenge_method": "S256",
            "state": state,
        })
        return f"https://accounts.google.com/o/oauth2/v2/auth?{query}"

    def google_oauth_callback(self, code: str | None, state: str | None, db: Session) -> AuthTokenResponse:
        from google.oauth2 import id_token as google_id_token
        from google.auth.transport import requests as google_requests
        from app.core.config import settings as app_settings

        logger.info("[GOOGLE OAUTH CALLBACK START]")
        logger.info("[GOOGLE OAUTH CALLBACK PARAMS] hasCode=%s hasState=%s", bool(code), bool(state))
        logger.info("[GOOGLE CLIENT SECRET CONFIGURED] %s", bool(app_settings.google_client_secret))
        logger.info("[GOOGLE REDIRECT URI] %s", app_settings.google_redirect_uri)
        if not code or not state:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Thiếu mã hoặc trạng thái OAuth.")

        parsed_state = self._parse_google_oauth_state(state)
        token_data = self._exchange_google_code(code, parsed_state["verifier"])

        id_token_value = token_data.get("id_token")
        try:
            logger.info("[GOOGLE OAUTH VERIFY ID TOKEN START]")
            google_data = google_id_token.verify_oauth2_token(
                id_token_value,
                google_requests.Request(),
                app_settings.google_client_id,
                clock_skew_in_seconds=10,
            )
        except Exception as exc:
            logger.warning("[GOOGLE OAUTH VERIFY ID TOKEN FAILED] error=%s", str(exc)[:240])
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google credential") from exc

        response = self._upsert_google_identity_user(google_data, db)
        logger.info("[GOOGLE OAUTH REDIRECT FRONTEND] url=%s/auth/callback?token=<redacted>", app_settings.frontend_url.rstrip("/"))
        return response

    def google_login(self, id_token: str | None, db: Session) -> AuthTokenResponse:
        from google.oauth2 import id_token as google_id_token
        from google.auth.transport import requests as google_requests
        from app.core.config import settings

        # Check if GOOGLE_CLIENT_ID is configured
        logger.info("[GOOGLE CLIENT ID BACKEND RAW] %s", repr(settings.google_client_id))
        
        if not settings.google_client_id:
            logger.error("[GOOGLE AUTH CONFIG ERROR] GOOGLE_CLIENT_ID is not set in backend .env file")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google OAuth is not configured on server. Please contact administrator.",
            )

        logger.info(
            "[GOOGLE CLIENT ID BACKEND CONFIGURED] prefix=%s",
            f"{settings.google_client_id[:20]}..." if settings.google_client_id else "MISSING"
        )

        logger.info(
            "[AUTH GOOGLE START] hasCredential=%s",
            bool(id_token),
        )

        if not id_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing Google credential",
            )

        try:
            google_data = google_id_token.verify_oauth2_token(
                id_token,
                google_requests.Request(),
                settings.google_client_id,
                clock_skew_in_seconds=10
            )
            logger.info("[AUTH GOOGLE VERIFY SUCCESS - RAW] aud=%s", google_data.get("aud"))
        except ValueError as exc:
            logger.warning("[AUTH GOOGLE VERIFY FAILED] ValueError: %s", str(exc)[:200])
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid Google credential: {exc}",
            ) from exc
        except Exception as exc:
            logger.warning("[AUTH GOOGLE VERIFY FAILED] Exception type=%s, msg=%s", type(exc).__name__, str(exc)[:200])
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid Google credential: {exc}",
            ) from exc

        return self._upsert_google_identity_user(google_data, db)
