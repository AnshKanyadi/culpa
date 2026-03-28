"""
Tests for email service — template rendering (no actual sending).
"""

from __future__ import annotations

from unittest.mock import patch, MagicMock

from server.services.email import (
    _wrap,
    send_welcome,
    send_first_session,
    send_session_expiring,
    send_limit_reached,
)


def test_wrap_produces_valid_html():
    html = _wrap("<p>Hello</p>")
    assert "<!DOCTYPE html>" in html
    assert "culpa" in html
    assert "<p>Hello</p>" in html


def test_wrap_includes_unsubscribe_link():
    html = _wrap("<p>test</p>", unsubscribe_url="https://example.com/unsub")
    assert "Unsubscribe" in html
    assert "https://example.com/unsub" in html


def test_wrap_no_unsubscribe_by_default():
    html = _wrap("<p>test</p>")
    assert "Unsubscribe" not in html


@patch("server.services.email._send")
def test_send_welcome(mock_send):
    mock_send.return_value = True
    result = send_welcome("user@example.com", "Alice")
    mock_send.assert_called_once()
    args = mock_send.call_args
    assert args[0][0] == "user@example.com"
    assert "Welcome" in args[0][1]
    assert "Alice" in args[0][2]
    assert result is True


@patch("server.services.email._send")
def test_send_welcome_no_name(mock_send):
    mock_send.return_value = True
    send_welcome("user@example.com")
    html = mock_send.call_args[0][2]
    assert "Hi there," in html


@patch("server.services.email._send")
def test_send_first_session(mock_send):
    mock_send.return_value = True
    send_first_session("user@example.com", "sess_123", "Fix auth bug")
    args = mock_send.call_args[0]
    assert "first" in args[1].lower()
    assert "Fix auth bug" in args[2]
    assert "sess_123" in args[2]


@patch("server.services.email._send")
def test_send_session_expiring(mock_send):
    mock_send.return_value = True
    send_session_expiring("user@example.com", "sess_456", "Debug agent", 18)
    args = mock_send.call_args[0]
    assert "expires" in args[1].lower()
    assert "18 hours" in args[2]
    assert "Upgrade" in args[2]


@patch("server.services.email._send")
def test_send_limit_reached(mock_send):
    mock_send.return_value = True
    send_limit_reached("user@example.com")
    args = mock_send.call_args[0]
    assert "limit" in args[1].lower()
    assert "Unlimited" in args[2]


def test_send_skips_without_api_key():
    """Without RESEND_API_KEY, _send returns False without error."""
    result = send_welcome("user@example.com")
    assert result is False
