"""
Tests for plan enforcement — free vs pro limits.
"""

from __future__ import annotations

import sqlite3
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone

from server.services.plans import (
    get_limits,
    check_can_upload,
    check_can_fork,
    compute_expires_at,
    delete_expired_sessions,
    get_user_usage,
    PLAN_LIMITS,
)


def test_free_plan_limits():
    limits = get_limits("free")
    assert limits["max_sessions"] == 3
    assert limits["retention_days"] == 7
    assert limits["max_forks_per_session"] == 5


def test_pro_plan_limits():
    limits = get_limits("pro")
    assert limits["max_sessions"] is None
    assert limits["retention_days"] == 90
    assert limits["max_forks_per_session"] is None


def test_unknown_plan_defaults_to_free():
    limits = get_limits("enterprise")
    assert limits == PLAN_LIMITS["free"]


def test_compute_expires_at_free():
    exp = compute_expires_at("free")
    exp_dt = datetime.fromisoformat(exp)
    # Should be ~7 days from now
    now = datetime.now(timezone.utc)
    delta = exp_dt - now
    assert 6 <= delta.days <= 7


def test_compute_expires_at_pro():
    exp = compute_expires_at("pro")
    exp_dt = datetime.fromisoformat(exp)
    now = datetime.now(timezone.utc)
    delta = exp_dt - now
    assert 89 <= delta.days <= 90


@patch("server.services.plans.get_session_count")
def test_check_can_upload_free_under_limit(mock_count):
    mock_count.return_value = 2
    allowed, reason = check_can_upload("user1", "free")
    assert allowed is True
    assert reason == ""


@patch("server.services.plans.get_session_count")
def test_check_can_upload_free_at_limit(mock_count):
    mock_count.return_value = 3
    allowed, reason = check_can_upload("user1", "free")
    assert allowed is False
    assert "Free tier limited to 3" in reason


@patch("server.services.plans.get_session_count")
def test_check_can_upload_pro_unlimited(mock_count):
    mock_count.return_value = 999
    allowed, reason = check_can_upload("user1", "pro")
    assert allowed is True


@patch("server.services.plans.get_fork_count")
def test_check_can_fork_free_under_limit(mock_count):
    mock_count.return_value = 3
    allowed, reason = check_can_fork("session1", "free")
    assert allowed is True


@patch("server.services.plans.get_fork_count")
def test_check_can_fork_free_at_limit(mock_count):
    mock_count.return_value = 5
    allowed, reason = check_can_fork("session1", "free")
    assert allowed is False
    assert "5 forks" in reason


@patch("server.services.plans.get_fork_count")
def test_check_can_fork_pro_unlimited(mock_count):
    mock_count.return_value = 500
    allowed, reason = check_can_fork("session1", "pro")
    assert allowed is True
