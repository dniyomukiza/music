"""Stripe checkout.session.completed webhook completes pending purchases (dev mode, no signature)."""
import json

import pytest

from e2e.support.fixture_factory import seed_pending_purchase


def _purchase_status(purchase_id: int) -> str:
    from glconnect import create_app
    from glconnect.book_platform_models import BookPurchase, TransactionStatus

    app, _ = create_app()
    with app.app_context():
        purchase = BookPurchase.query.get(purchase_id)
        if not purchase:
            return "missing"
        status = purchase.status
        if status == TransactionStatus.COMPLETED:
            return "completed"
        return getattr(status, "value", str(status))


@pytest.mark.buyer
@pytest.mark.integration
def test_checkout_session_completed_webhook_finishes_purchase(
    page, e2e_config, test_published_digital_book, test_buyer, user_registry
):
    book = test_published_digital_book
    user_registry.track(test_buyer)
    user_registry.track(book.author_user)

    purchase_id = seed_pending_purchase(test_buyer, book, amount=2.99)
    amount_cents = 299

    payload = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "client_reference_id": str(purchase_id),
                "metadata": {"book_id": str(book.book_id)},
                "amount_total": amount_cents,
                "payment_intent": "pi_e2e_test_webhook",
                "customer_details": {"email": test_buyer.email},
            }
        },
    }

    base = e2e_config.base_url.rstrip("/")
    resp = page.request.post(
        f"{base}/mybook/stripe/webhook",
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload),
    )
    assert resp.ok, f"webhook failed: {resp.status} {resp.text()[:300]}"
    assert _purchase_status(purchase_id) == "completed"
