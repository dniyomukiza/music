"""Buyer campaign discovery (partial workflow)."""
import pytest
from playwright.sync_api import expect

from e2e.workflows.buyer import BuyerWorkflow


@pytest.mark.campaign
@pytest.mark.buyer
def test_buyer_can_open_campaign_discovery(page, context, e2e_config, test_buyer, test_live_campaign):
    wf = BuyerWorkflow(page, context, e2e_config)
    wf.login(test_buyer, next_path="/mybook/investments")
    expect(page.locator("body")).to_contain_text(test_live_campaign.title, timeout=30000)
