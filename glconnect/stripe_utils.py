import os
import stripe
from flask import current_app


def init_stripe():
    """
    Initialize Stripe with the secret key from configuration or environment.
    This should be called lazily (on-demand) to avoid import-time issues.
    """
    secret_key = (
        getattr(current_app, "config", {}).get("STRIPE_SECRET_KEY")
        if hasattr(current_app, "config")
        else None
    ) or os.getenv("STRIPE_SECRET_KEY")

    if not secret_key:
        raise RuntimeError("STRIPE_SECRET_KEY is not configured")

    stripe.api_key = secret_key
    return stripe


def get_webhook_secret():
    """
    Get the Stripe webhook secret used to verify incoming webhook signatures.
    """
    return (
        getattr(current_app, "config", {}).get("STRIPE_WEBHOOK_SECRET")
        if hasattr(current_app, "config")
        else None
    ) or os.getenv("STRIPE_WEBHOOK_SECRET")

