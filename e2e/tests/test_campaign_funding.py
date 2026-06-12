"""Buyer discovers and funds a campaign (standalone slice)."""
import pytest
from playwright.sync_api import expect

from e2e.workflows.buyer import BuyerWorkflow


@pytest.mark.campaign
@pytest.mark.buyer
def test_buyer_finds_campaign_on_investments(page, e2e_config, test_live_campaign, test_buyer):
    wf = BuyerWorkflow(page, page.context, e2e_config)
    wf.login(test_buyer, next_path="/mybook/investments")
    expect(page.locator("body")).to_contain_text(test_live_campaign.title, timeout=30000)


@pytest.mark.campaign
@pytest.mark.buyer
@pytest.mark.stripe
def test_buyer_funds_campaign(page, context, e2e_config, test_live_campaign, test_buyer):
    if not e2e_config.stripe_enabled:
        pytest.skip("STRIPE_SECRET_FOR_TEST (sk_test_*) not configured")

    wf = BuyerWorkflow(page, context, e2e_config)
    wf.login(test_buyer)
    wf.fund_campaign(test_live_campaign.campaign_id, amount="10.00")
    page.goto(f"{e2e_config.base_url}/mybook/investments/{test_live_campaign.campaign_id}")
    expect(page.locator("body")).to_contain_text("10", timeout=30000)
