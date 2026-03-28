"""Auth and API key routes."""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel, field_validator

from ..services.auth import (
    hash_password, verify_password, create_access_token,
    decode_access_token, generate_api_key, hash_api_key,
)
from ..services.plans import get_user_usage
from ..services.email import send_welcome
from ..storage.user_repository import UserRepository, ApiKeyRepository
from culpa.utils.ids import generate_ulid

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["auth"])

user_repo = UserRepository()
key_repo = ApiKeyRepository()


class RegisterRequest(BaseModel):
    """Registration payload with email, password, and optional name."""
    email: str
    password: str
    name: Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    """Login payload with email and password."""
    email: str
    password: str


class CreateKeyRequest(BaseModel):
    """Payload for creating a named API key."""
    name: str = "Default"


def get_current_user(culpa_token: Optional[str] = Cookie(None)) -> dict:
    """Extract and validate the current user from the JWT cookie."""
    if not culpa_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_access_token(culpa_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = user_repo.get_by_id(payload["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def get_current_user_from_api_key(authorization: Optional[str] = None) -> Optional[dict]:
    """Extract user from Bearer API key header, returning None if no key provided."""
    if not authorization or not authorization.startswith("Bearer culpa_"):
        return None
    key = authorization.removeprefix("Bearer ")
    key_hash = hash_api_key(key)
    key_record = key_repo.get_by_hash(key_hash)
    if not key_record:
        return None
    key_repo.touch_last_used(key_record["id"])
    return user_repo.get_by_id(key_record["user_id"])


@router.post("/auth/register", status_code=201)
async def register(body: RegisterRequest, response: Response) -> dict:
    """Register a new user account and set the auth cookie."""
    if user_repo.email_exists(body.email):
        raise HTTPException(status_code=409, detail="Email already registered")
    user_id = generate_ulid()
    password_hash = hash_password(body.password)
    user = user_repo.create(user_id, body.email, password_hash, body.name)
    token = create_access_token(user["id"], user["email"])
    response.set_cookie(
        key="culpa_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=72 * 3600,
        secure=False,
    )
    try:
        send_welcome(body.email, body.name)
    except Exception:
        pass

    return {"user": user}


@router.post("/auth/login")
async def login(body: LoginRequest, response: Response) -> dict:
    """Authenticate with email/password and set the auth cookie."""
    user = user_repo.get_by_email(body.email)
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(user["id"], user["email"])
    response.set_cookie(
        key="culpa_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=72 * 3600,
        secure=False,
    )
    safe_user = {k: v for k, v in user.items() if k != "password_hash"}
    return {"user": safe_user}


@router.post("/auth/logout")
async def logout(response: Response) -> dict:
    """Clear the auth cookie."""
    response.delete_cookie("culpa_token")
    return {"ok": True}


@router.get("/auth/me")
async def me(current_user: dict = Depends(get_current_user)) -> dict:
    """Return the currently authenticated user."""
    return {"user": current_user}


@router.post("/keys", status_code=201)
async def create_api_key(
    body: CreateKeyRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Generate a new API key. The full key is returned only once."""
    full_key, key_hash, key_prefix = generate_api_key()
    key_id = generate_ulid()
    key_record = key_repo.create(key_id, current_user["id"], key_hash, key_prefix, body.name)
    return {"key": full_key, "record": key_record}


@router.get("/keys")
async def list_api_keys(current_user: dict = Depends(get_current_user)) -> dict:
    """List all API keys for the current user."""
    keys = key_repo.list_for_user(current_user["id"])
    return {"keys": keys}


@router.delete("/keys/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: str,
    current_user: dict = Depends(get_current_user),
) -> None:
    """Revoke an API key by ID."""
    revoked = key_repo.revoke(key_id, current_user["id"])
    if not revoked:
        raise HTTPException(status_code=404, detail="API key not found")


@router.get("/usage")
async def usage(current_user: dict = Depends(get_current_user)) -> dict:
    """Return plan usage stats for the current user."""
    return get_user_usage(current_user["id"], current_user.get("plan", "free"))
