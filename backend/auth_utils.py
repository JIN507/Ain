# auth_utils.py
# Authentication utilities: password hashing, JWT creation/verification, CSRF token helpers.

from datetime import datetime, timedelta, timezone
import os
import secrets
from typing import Optional, Dict, Any

import bcrypt
import jwt

from models import User


def _get_env(name: str, default: Optional[str] = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


JWT_SECRET = _get_env("JWT_SECRET", "dev-secret-change-me")
ACCESS_TTL_SECONDS = int(os.getenv("ACCESS_TTL", "900"))  # 15m
REFRESH_TTL_SECONDS = int(os.getenv("REFRESH_TTL", "604800"))  # 7d


def hash_password(plain: str) -> str:
    if not plain:
        raise ValueError("Password cannot be empty")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def _base_claims(user: User) -> Dict[str, Any]:
    return {
        "sub": str(user.id),
        "role": user.role,
        "must_change_password": user.must_change_password,
    }


def create_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        **_base_claims(user),
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ACCESS_TTL_SECONDS)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def create_refresh_token(user: User, jti: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        **_base_claims(user),
        "type": "refresh",
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=REFRESH_TTL_SECONDS)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def mask_email(email: str) -> str:
    try:
        local, domain = email.split("@", 1)
        if len(local) <= 2:
            return "*" * len(local) + "@" + domain
        return local[0] + "*" * (len(local) - 2) + local[-1] + "@" + domain
    except Exception:
        return "***"
