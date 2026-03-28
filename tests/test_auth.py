"""
Tests for auth service — password hashing, JWT tokens, API key generation.
"""

from __future__ import annotations

import pytest
from server.services.auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    generate_api_key,
    hash_api_key,
)


def test_password_hash_and_verify():
    hashed = hash_password("supersecret")
    assert hashed != "supersecret"
    assert verify_password("supersecret", hashed)
    assert not verify_password("wrongpassword", hashed)


def test_jwt_roundtrip():
    token = create_access_token("user_123", "test@example.com")
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "user_123"
    assert payload["email"] == "test@example.com"


def test_jwt_invalid_token():
    payload = decode_access_token("not.a.valid.token")
    assert payload is None


def test_generate_api_key_format():
    full_key, key_hash, key_prefix = generate_api_key()
    assert full_key.startswith("culpa_")
    assert len(full_key) == 54  # "culpa_" (6) + 48 chars
    assert key_prefix == full_key[:12]
    assert key_hash == hash_api_key(full_key)


def test_api_key_uniqueness():
    key1, _, _ = generate_api_key()
    key2, _, _ = generate_api_key()
    assert key1 != key2


def test_api_key_hash_is_deterministic():
    full_key, key_hash, _ = generate_api_key()
    assert hash_api_key(full_key) == key_hash
    assert hash_api_key(full_key) == key_hash  # same input, same hash
