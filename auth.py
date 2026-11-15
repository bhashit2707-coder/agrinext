"""Password hashing and opaque, revocable cookie-session authentication."""
import hashlib
import hmac
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import Cookie, HTTPException, status

import database

SESSION_COOKIE_NAME = "agrinext_session"
SESSION_TTL_HOURS = int(os.getenv("AGRINEXT_SESSION_TTL_HOURS", "12"))
PBKDF2_ITERATIONS = 310_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        calculated = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        ).hex()
        return hmac.compare_digest(calculated, digest_hex)
    except (ValueError, TypeError):
        return False


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session_for_user(user_id: str) -> str:
    token = secrets.token_urlsafe(48)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=SESSION_TTL_HOURS)
    database.create_session(str(uuid.uuid4()), user_id, hash_session_token(token), expires_at.isoformat())
    return token


def get_current_user(agrinext_session: Optional[str] = Cookie(default=None)) -> Dict[str, Any]:
    if not agrinext_session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    user = database.get_user_by_session_hash(hash_session_token(agrinext_session))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session is invalid or expired")
    return user


def revoke_token(token: Optional[str]) -> None:
    if token:
        database.revoke_session(hash_session_token(token))


def get_optional_current_user(agrinext_session: Optional[str] = Cookie(default=None)) -> Optional[Dict[str, Any]]:
    """Allow public coordinate-only NASA requests; farm-linked requests must authenticate."""
    if not agrinext_session:
        return None
    return database.get_user_by_session_hash(hash_session_token(agrinext_session))
