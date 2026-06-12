"""Standalone payout / Stripe Connect slice."""
import pytest

from e2e.pages.earnings import EarningsPage
from e2e.pages.payout_setup import PayoutSetupPage
from e2e.workflows.author import AuthorWorkflow


@pytest.mark.payout
@pytest.mark.author
def test_author_reaches_payout_setup(page, e2e_config, test_author_with_profile):
    AuthorWorkflow(page, e2e_config).login(test_author_with_profile)
    PayoutSetupPage(page, e2e_config).open()
    assert page.locator("#btnStripeConnect").is_visible()


@pytest.mark.payout
@pytest.mark.author
@pytest.mark.stripe
def test_author_opens_stripe_connect_onboarding(page, context, e2e_config, test_author_with_profile):
    if not e2e_config.stripe_enabled:
        pytest.skip("STRIPE_SECRET_FOR_TEST (sk_test_*) not configured")

    wf = AuthorWorkflow(page, e2e_config)
    wf.login(test_author_with_profile)
    wf.start_connect_onboarding(context)


@pytest.mark.payout
@pytest.mark.author
def test_author_earnings_dashboard_loads(page, e2e_config, test_author_with_profile):
    AuthorWorkflow(page, e2e_config).login(test_author_with_profile)
    EarningsPage(page, e2e_config).open()
    EarningsPage(page, e2e_config).expect_loaded()
