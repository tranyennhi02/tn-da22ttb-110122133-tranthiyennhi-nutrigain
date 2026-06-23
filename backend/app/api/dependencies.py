from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.entities import User
from app.repositories.user_repository import UserRepository


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is required",
        )

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
        print(f"[AUTH TOKEN DECODED] sub={payload.get('sub')}, user_id={user_id}")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc

    user = UserRepository(db).get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    print(f"[GET CURRENT USER] user_id={user.id}, email={user.email}")
    user_status = str(getattr(user, "status", "") or "").upper()
    if not user.is_active or user_status == "LOCKED":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tài khoản đã bị khóa.")
    return user


def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    """Return current user or None without raising on missing/invalid token or DB errors."""
    try:
        if credentials is None or credentials.scheme.lower() != "bearer":
            return None

        try:
            payload = decode_access_token(credentials.credentials)
            user_id = int(payload["sub"])
        except Exception:
            return None

        try:
            user = UserRepository(db).get_by_id(user_id)
        except Exception:
            # DB error — treat as unauthenticated to avoid 500 in routes
            return None

        if user is None:
            return None
        user_status = str(getattr(user, "status", "") or "").upper()
        if not user.is_active or user_status == "LOCKED":
            return None
        return user
    except Exception:
        return None


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if str(current_user.role or "").upper() not in {"ADMIN", "SUPER_ADMIN"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền truy cập chức năng quản trị.",
        )
    return current_user
