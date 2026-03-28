"""Transactional email service via Resend."""
from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
FROM_EMAIL = os.environ.get("FROM_EMAIL", "noreply@culpa.dev")
APP_URL = os.environ.get("CULPA_CLOUD_URL", "https://app.culpa.dev")


def _send(to: str, subject: str, html: str) -> bool:
    """Send an email via Resend. Silently skips if RESEND_API_KEY is not set."""
    if not RESEND_API_KEY:
        logger.debug(f"Email skipped (no RESEND_API_KEY): {subject} -> {to}")
        return False

    try:
        import resend
        resend.api_key = RESEND_API_KEY
        resend.Emails.send({
            "from": FROM_EMAIL,
            "to": [to],
            "subject": subject,
            "html": html,
        })
        logger.info(f"Email sent: {subject} -> {to}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}", exc_info=True)
        return False


def _wrap(body: str, unsubscribe_url: Optional[str] = None) -> str:
    """Wrap email body in the Culpa dark-themed HTML template."""
    unsub = ""
    if unsubscribe_url:
        unsub = f'<p style="margin-top:32px;font-size:11px;color:#666;"><a href="{unsubscribe_url}" style="color:#888;">Unsubscribe</a></p>'

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:40px 20px;background:#0a0a0b;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <div style="max-width:480px;margin:0 auto;">
    <div style="margin-bottom:24px;">
      <a href="{APP_URL}" style="text-decoration:none;"><span style="font-family:'JetBrains Mono',monospace;font-weight:bold;font-size:18px;color:#e8e8ea;letter-spacing:-0.5px;">culpa</span></a><span style="font-family:'JetBrains Mono',monospace;font-size:11px;color:#8888a0;margin-left:8px;">— culpa.dev</span>
    </div>
    <div style="color:#e8e8ea;font-size:14px;line-height:1.7;">
      {body}
    </div>
    {unsub}
  </div>
</body>
</html>"""


def send_welcome(to: str, name: Optional[str] = None) -> bool:
    """Send the welcome email after registration."""
    greeting = f"Hi {name}," if name else "Hi there,"
    html = _wrap(f"""
    <p>{greeting}</p>
    <p>Welcome to Culpa — the flight recorder for AI agents.</p>
    <p>Here's how to record your first session:</p>
    <div style="background:#141415;border:1px solid #1e1e21;border-radius:8px;padding:16px;margin:16px 0;">
      <code style="font-family:'JetBrains Mono',monospace;font-size:13px;color:#4f8ef7;line-height:1.8;">
        pip install culpa<br>
        culpa login<br>
        culpa record "Fix auth bug" -- python agent.py
      </code>
    </div>
    <p>Or in Python:</p>
    <div style="background:#141415;border:1px solid #1e1e21;border-radius:8px;padding:16px;margin:16px 0;">
      <code style="font-family:'JetBrains Mono',monospace;font-size:13px;color:#4f8ef7;line-height:1.8;">
        import culpa<br>
        culpa.init("Fix auth bug")<br>
        # your agent runs here<br>
        session = culpa.stop()
      </code>
    </div>
    <p>Once recorded, open the <a href="{APP_URL}" style="color:#f75f5f;text-decoration:none;">dashboard</a> to explore, replay, and fork your session.</p>
    <p style="color:#8888a0;">— The Culpa team</p>
    """)
    return _send(to, "Welcome to Culpa — here's how to record your first session", html)


def send_first_session(to: str, session_id: str, session_name: str) -> bool:
    """Send a notification after the user's first session upload."""
    html = _wrap(f"""
    <p>Your first Culpa session is ready to explore.</p>
    <div style="background:#141415;border:1px solid #1e1e21;border-radius:8px;padding:16px;margin:16px 0;">
      <p style="margin:0;font-size:13px;color:#8888a0;">Session</p>
      <p style="margin:4px 0 0;font-size:15px;font-weight:600;color:#e8e8ea;">{session_name}</p>
    </div>
    <p>
      <a href="{APP_URL}/session/{session_id}" style="display:inline-block;background:#f75f5f;color:white;text-decoration:none;padding:10px 20px;border-radius:6px;font-weight:600;font-size:13px;">
        View in Dashboard
      </a>
    </p>
    <p style="margin-top:16px;">From the dashboard you can:</p>
    <ul style="color:#8888a0;padding-left:20px;">
      <li>Replay the full session deterministically</li>
      <li>Fork at any LLM call to test what-if scenarios</li>
      <li>Inspect file diffs and terminal output</li>
    </ul>
    """)
    return _send(to, "Your first Culpa session is ready to explore", html)


def send_session_expiring(to: str, session_id: str, session_name: str, hours_left: int) -> bool:
    """Remind free-tier users 1 day before a session expires."""
    html = _wrap(f"""
    <p>Your Culpa session <strong>{session_name}</strong> expires in about {hours_left} hours.</p>
    <p>Free tier sessions are retained for 7 days. After that, the session and all its events are permanently deleted.</p>
    <p>
      <a href="{APP_URL}/settings/billing" style="display:inline-block;background:#f75f5f;color:white;text-decoration:none;padding:10px 20px;border-radius:6px;font-weight:600;font-size:13px;">
        Upgrade to Pro — 90-day retention
      </a>
    </p>
    <p style="color:#8888a0;font-size:12px;">Or <a href="{APP_URL}/session/{session_id}" style="color:#4f8ef7;text-decoration:none;">view the session</a> before it expires.</p>
    """, unsubscribe_url=f"{APP_URL}/settings/notifications")
    return _send(to, f"Your Culpa session expires tomorrow", html)


def send_limit_reached(to: str) -> bool:
    """Notify a free-tier user that they've hit the 3-session limit."""
    html = _wrap(f"""
    <p>You've reached the free tier limit of 3 cloud sessions.</p>
    <p>New uploads will be rejected until you delete an existing session or upgrade your plan.</p>
    <p><strong>Culpa Pro ($29/month)</strong> includes:</p>
    <ul style="color:#e8e8ea;padding-left:20px;">
      <li>Unlimited cloud sessions</li>
      <li>90-day retention (vs 7 days)</li>
      <li>Unlimited fork history</li>
      <li>Team sharing</li>
    </ul>
    <p>
      <a href="{APP_URL}/settings/billing" style="display:inline-block;background:#f75f5f;color:white;text-decoration:none;padding:10px 20px;border-radius:6px;font-weight:600;font-size:13px;">
        Upgrade to Pro
      </a>
    </p>
    """, unsubscribe_url=f"{APP_URL}/settings/notifications")
    return _send(to, "You've hit the free tier limit", html)
