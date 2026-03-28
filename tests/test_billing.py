"""
Tests for billing — webhook handling, plan updates.
"""

from __future__ import annotations

import sqlite3
import pytest
from unittest.mock import patch, MagicMock

from server.api.billing import (
    _handle_checkout_completed,
    _handle_subscription_deleted,
    _handle_payment_failed,
    _update_user_plan,
    _get_user_by_stripe_customer,
)
from server.storage.database import init_db, get_db, _connection


@pytest.fixture(autouse=True)
def setup_db(tmp_path):
    """Set up a fresh in-memory database for each test."""
    import server.storage.database as db_mod
    db_mod._connection = None
    conn = init_db(str(tmp_path / "test.db"))

    # Create a test user
    conn.execute(
        "INSERT INTO users (id, email, password_hash, name, plan) VALUES (?, ?, ?, ?, ?)",
        ("user1", "test@example.com", "fakehash", "Test User", "free"),
    )
    conn.commit()
    yield
    db_mod._connection = None


def test_update_user_plan():
    _update_user_plan("user1", "pro", stripe_customer_id="cus_123", stripe_subscription_id="sub_456")
    with get_db() as db:
        row = db.execute("SELECT plan, stripe_customer_id, stripe_subscription_id FROM users WHERE id = ?", ("user1",)).fetchone()
    assert row["plan"] == "pro"
    assert row["stripe_customer_id"] == "cus_123"
    assert row["stripe_subscription_id"] == "sub_456"


def test_get_user_by_stripe_customer():
    _update_user_plan("user1", "free", stripe_customer_id="cus_abc")
    user = _get_user_by_stripe_customer("cus_abc")
    assert user is not None
    assert user["id"] == "user1"


def test_get_user_by_stripe_customer_not_found():
    user = _get_user_by_stripe_customer("cus_nonexistent")
    assert user is None


def test_handle_checkout_completed():
    _handle_checkout_completed({
        "customer": "cus_test",
        "subscription": "sub_test",
        "metadata": {"culpa_user_id": "user1"},
    })
    with get_db() as db:
        row = db.execute("SELECT plan, stripe_subscription_id FROM users WHERE id = ?", ("user1",)).fetchone()
    assert row["plan"] == "pro"
    assert row["stripe_subscription_id"] == "sub_test"


def test_handle_subscription_deleted():
    # First upgrade
    _update_user_plan("user1", "pro", stripe_customer_id="cus_del", stripe_subscription_id="sub_del")
    # Then cancel
    _handle_subscription_deleted({"customer": "cus_del"})
    with get_db() as db:
        row = db.execute("SELECT plan FROM users WHERE id = ?", ("user1",)).fetchone()
    assert row["plan"] == "free"


def test_handle_payment_failed_sets_grace_period():
    _update_user_plan("user1", "pro", stripe_customer_id="cus_fail")
    _handle_payment_failed({"customer": "cus_fail"})
    with get_db() as db:
        row = db.execute("SELECT plan, plan_expires_at FROM users WHERE id = ?", ("user1",)).fetchone()
    assert row["plan"] == "pro"  # still pro during grace period
    assert row["plan_expires_at"] is not None
