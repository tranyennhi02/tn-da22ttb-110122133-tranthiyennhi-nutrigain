from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from datetime import timedelta
from typing import Any

from app.core.config import settings

try:  # bcrypt is used in Docker/production when installed from requirements.
    import bcrypt as _bcrypt
except Exception:  # pragma: no cover - local fallback when dependency is absent.
    _bcrypt = None


JWT_ALGORITHM = "HS256"


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("ascii"))


def hash_password(password: str) -> str:
    if _bcrypt is not None:
        hashed = _bcrypt.hashpw(password.encode("utf-8"), _bcrypt.gensalt())
        return "bcrypt$" + hashed.decode("utf-8")

    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)
    return "scrypt$16384$8$1$" + _b64url_encode(salt) + "$" + _b64url_encode(derived)


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False

    if password_hash.startswith("bcrypt$"):
        if _bcrypt is None:
            return False
        stored = password_hash.removeprefix("bcrypt$").encode("utf-8")
        return bool(_bcrypt.checkpw(password.encode("utf-8"), stored))

    if password_hash.startswith("$2a$") or password_hash.startswith("$2b$"):
        if _bcrypt is None:
            return False
        return bool(_bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8")))

    if password_hash.startswith("scrypt$"):
        try:
            _, n_value, r_value, p_value, salt_b64, digest_b64 = password_hash.split("$", 5)
            salt = _b64url_decode(salt_b64)
            expected = _b64url_decode(digest_b64)
            derived = hashlib.scrypt(
                password.encode("utf-8"),
                salt=salt,
                n=int(n_value),
                r=int(r_value),
                p=int(p_value),
            )
            return hmac.compare_digest(derived, expected)
        except Exception:
            return False

    return False


def create_access_token(
    subject: str,
    extra_claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    now = int(time.time())
    if expires_delta is not None:
        expire_seconds = max(1, int(expires_delta.total_seconds()))
    else:
        minutes = getattr(settings, "access_token_expire_minutes", None)
        try:
            minutes = int(minutes)
        except (TypeError, ValueError):
            minutes = 60 * 24

        if minutes <= 0:
            minutes = 60 * 24

        expire_seconds = int(timedelta(minutes=minutes).total_seconds())
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "exp": now + expire_seconds,
    }
    if extra_claims:
        payload.update(extra_claims)

    encoded_header = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    signature = hmac.new(
        settings.jwt_secret_key.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()
    return f"{encoded_header}.{encoded_payload}.{_b64url_encode(signature)}"


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".", 2)
    except ValueError as exc:
        raise ValueError("Invalid token format") from exc

    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    expected_signature = hmac.new(
        settings.jwt_secret_key.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()
    actual_signature = _b64url_decode(encoded_signature)
    if not hmac.compare_digest(actual_signature, expected_signature):
        raise ValueError("Invalid token signature")

    header = json.loads(_b64url_decode(encoded_header))
    if header.get("alg") != JWT_ALGORITHM:
        raise ValueError("Unsupported token algorithm")

    payload = json.loads(_b64url_decode(encoded_payload))
    if int(payload.get("exp", 0)) < int(time.time()):
        raise ValueError("Token has expired")
    return payload
