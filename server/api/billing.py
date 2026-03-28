"""Stripe billing routes for checkout, webhooks, and subscription management."""
from __future__ import annotations

import logging
import os
from typing import Optional

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request

from ..dependencies import require_user
from ..storage.database import get_db
from ..storage.user_repository import UserRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/billing", tags=["billing"])

user_repo = UserRepository()

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_ID = os.environ.get("STRIPE_PRICE_ID", "")

stripe.api_key = STRIPE_SECRET_KEY

NOT_CONFIGURED = {"error": "Billing not configured", "code": "not_configured"}


def _update_user_plan(
    user_id: str,
    plan: str,
    stripe_customer_id: Optional[str] = None,
    stripe_subscription_id: Optional[str] = None,
    plan_expires_at: Optional[str] = None,
) -> None:
    """Write plan and Stripe metadata fields for a user."""
    with get_db() as db:
        db.execute(
            """UPDATE users SET plan = ?, stripe_customer_id = COALESCE(?, stripe_customer_id),
               stripe_subscription_id = COALESCE(?, stripe_subscription_id),
               plan_expires_at = ?, updated_at = datetime('now')
               WHERE id = ?""",
            (plan, stripe_customer_id, stripe_subscription_id, plan_expires_at, user_id),
        )


def _get_user_by_stripe_customer(customer_id: str) -> Optional[dict]:
    """Look up a user by their Stripe customer ID."""
    with get_db() as db:
        row = db.execute(
            "SELECT id, email, name, plan, created_at FROM users WHERE stripe_customer_id = ?",
            (customer_id,),
        ).fetchone()
        return dict(row) if row else None


@router.post("/create-checkout")
async def create_checkout(current_user: dict = Depends(require_user)) -> dict:
    """Create a Stripe Checkout session for the Pro plan."""
    if not STRIPE_SECRET_KEY or not STRIPE_PRICE_ID:
        return NOT_CONFIGURED | {"status_code": 503}

    if current_user.get("plan") == "pro":
        raise HTTPException(status_code=400, detail="Already on Pro plan")

    try:
        with get_db() as db:
            row = db.execute(
                "SELECT stripe_customer_id FROM users WHERE id = ?",
                (current_user["id"],),
            ).fetchone()
            stripe_customer_id = row["stripe_customer_id"] if row and row["stripe_customer_id"] else None

        if not stripe_customer_id:
            customer = stripe.Customer.create(
                email=current_user["email"],
                name=current_user.get("name"),
                metadata={"culpa_user_id": current_user["id"]},
            )
            stripe_customer_id = customer.id
            _update_user_plan(current_user["id"], "free", stripe_customer_id=stripe_customer_id)

        session = stripe.checkout.Session.create(
            customer=stripe_customer_id,
            mode="subscription",
            line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
            success_url=os.environ.get("CULPA_CLOUD_URL", "http://localhost:5173") + "/settings/billing/success",
            cancel_url=os.environ.get("CULPA_CLOUD_URL", "http://localhost:5173") + "/settings/billing",
            metadata={"culpa_user_id": current_user["id"]},
        )
        return {"checkout_url": session.url}

    except stripe.StripeError as e:
        logger.error(f"Stripe error creating checkout: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail="Failed to create checkout session")
    except Exception as e:
        logger.error(f"Unexpected error in create_checkout: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/webhook")
async def stripe_webhook(request: Request, stripe_signature: Optional[str] = Header(None)) -> dict:
    """Handle incoming Stripe webhook events."""
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Webhook secret not configured")

    body = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            body, stripe_signature, STRIPE_WEBHOOK_SECRET
        )
    except stripe.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webhook error: {e}")

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        _handle_checkout_completed(data)
    elif event_type == "customer.subscription.deleted":
        _handle_subscription_deleted(data)
    elif event_type == "invoice.payment_failed":
        _handle_payment_failed(data)

    return {"received": True}


def _handle_checkout_completed(session: dict) -> None:
    """Upgrade user to Pro after successful checkout."""
    customer_id = session.get("customer")
    subscription_id = session.get("subscription")
    culpa_user_id = session.get("metadata", {}).get("culpa_user_id")

    if culpa_user_id:
        _update_user_plan(
            culpa_user_id,
            plan="pro",
            stripe_customer_id=customer_id,
            stripe_subscription_id=subscription_id,
        )
        logger.info(f"User {culpa_user_id} upgraded to Pro")
    elif customer_id:
        user = _get_user_by_stripe_customer(customer_id)
        if user:
            _update_user_plan(
                user["id"],
                plan="pro",
                stripe_subscription_id=subscription_id,
            )
            logger.info(f"User {user['id']} upgraded to Pro via customer lookup")


def _handle_subscription_deleted(subscription: dict) -> None:
    """Downgrade user to free when subscription is cancelled."""
    customer_id = subscription.get("customer")
    if not customer_id:
        return

    user = _get_user_by_stripe_customer(customer_id)
    if user:
        _update_user_plan(user["id"], plan="free", stripe_subscription_id=None)
        logger.info(f"User {user['id']} downgraded to free (subscription cancelled)")


def _handle_payment_failed(invoice: dict) -> None:
    """Set a 7-day grace period on payment failure before downgrade."""
    from datetime import datetime, timedelta, timezone

    customer_id = invoice.get("customer")
    if not customer_id:
        return

    user = _get_user_by_stripe_customer(customer_id)
    if user:
        grace_end = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        _update_user_plan(user["id"], plan="pro", plan_expires_at=grace_end)
        logger.warning(f"Payment failed for user {user['id']}, grace period until {grace_end}")


@router.get("/status")
async def billing_status(current_user: dict = Depends(require_user)) -> dict:
    """Return the current subscription status for the authenticated user."""
    if not STRIPE_SECRET_KEY:
        return NOT_CONFIGURED

    with get_db() as db:
        row = db.execute(
            "SELECT plan, stripe_customer_id, stripe_subscription_id, plan_expires_at FROM users WHERE id = ?",
            (current_user["id"],),
        ).fetchone()

    if not row:
        return {"plan": "free", "subscription": None}

    result = {
        "plan": row["plan"],
        "stripe_customer_id": row["stripe_customer_id"],
        "has_subscription": row["stripe_subscription_id"] is not None,
        "plan_expires_at": row["plan_expires_at"],
    }

    if row["stripe_subscription_id"] and STRIPE_SECRET_KEY:
        try:
            sub = stripe.Subscription.retrieve(row["stripe_subscription_id"])
            result["subscription"] = {
                "status": sub.status,
                "current_period_end": sub.current_period_end,
                "cancel_at_period_end": sub.cancel_at_period_end,
            }
        except stripe.StripeError:
            result["subscription"] = None
    else:
        result["subscription"] = None

    return result


@router.post("/portal")
async def create_portal(current_user: dict = Depends(require_user)) -> dict:
    """Create a Stripe Customer Portal session for managing the subscription."""
    if not STRIPE_SECRET_KEY:
        return NOT_CONFIGURED

    with get_db() as db:
        row = db.execute(
            "SELECT stripe_customer_id FROM users WHERE id = ?",
            (current_user["id"],),
        ).fetchone()

    if not row or not row["stripe_customer_id"]:
        raise HTTPException(status_code=400, detail="No billing account found. Subscribe to Pro first.")

    try:
        session = stripe.billing_portal.Session.create(
            customer=row["stripe_customer_id"],
            return_url=os.environ.get("CULPA_CLOUD_URL", "http://localhost:5173") + "/settings/billing",
        )
        return {"portal_url": session.url}
    except stripe.StripeError as e:
        logger.error(f"Stripe error creating portal: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail="Failed to create billing portal")
    except Exception as e:
        logger.error(f"Unexpected error in create_portal: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
