#!/usr/bin/env python3
"""Regression check for mandatory Stripe webhook signature verification."""

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def main():
    routes = (ROOT / "glconnect" / "book_platform_routes.py").read_text(encoding="utf-8")
    start = routes.find("def stripe_webhook():")
    end = routes.find("        # Helper function to complete a purchase", start)
    handler = routes[start:end]

    failures = []
    if "stripe.Webhook.construct_event" not in handler:
        failures.append("webhook handler should verify Stripe signatures with construct_event")
    if "json.loads(payload)" in handler:
        failures.append("webhook handler should not parse unsigned JSON payloads")
    if "not current_app.debug" in handler:
        failures.append("webhook signature enforcement should not depend on debug mode")
    if "Webhook verification required" not in handler:
        failures.append("webhook handler should reject requests missing verification inputs")

    if failures:
        print("FAILURES:")
        for failure in failures:
            print(" -", failure)
        sys.exit(1)

    print("OK: Stripe webhook requires signed payloads")


if __name__ == "__main__":
    main()
