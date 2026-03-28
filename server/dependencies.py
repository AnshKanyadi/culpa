"""Shared FastAPI dependencies for authentication."""
from __future__ import annotations

from typing import Optional

from fastapi import Cookie, Header, HTTPException

from .services.auth import decode_access_token, hash_api_key
from .storage.user_repository import UserRepository, ApiKeyRepository

user_repo = UserRepository()
key_repo = ApiKeyRepository()


def get_current_user_optional(
    culpa_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None),
) -> Optional[dict]:
    """Resolve current user from JWT cookie or API key header, returning None if unauthenticated."""
    if authorization and authorization.startswith("Bearer culpa_"):
        key = authorization.removeprefix("Bearer ")
        key_hash = hash_api_key(key)
        key_record = key_repo.get_by_hash(key_hash)
        if key_record:
            key_repo.touch_last_used(key_record["id"])
            return user_repo.get_by_id(key_record["user_id"])

    if culpa_token:
        payload = decode_access_token(culpa_token)
        if payload:
            return user_repo.get_by_id(payload["sub"])

    return None


def require_user(
    culpa_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None),
) -> dict:
    """Resolve current user or raise 401 if not authenticated."""
    user = get_current_user_optional(culpa_token=culpa_token, authorization=authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user
