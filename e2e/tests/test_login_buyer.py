"""Buyer login only — partial workflow slice (no register, profile, or purchase)."""
import re

import pytest
from playwright.sync_api import expect

from e2e.pages.auth import LoginPage
from e2e.workflows.buyer import BuyerWorkflow

_MARKETPLACE_URL = re.compile(r"/mybook/marketplace")


@pytest.mark.smoke
@pytest.mark.auth
@pytest.mark.buyer
def test_seeded_buyer_login_reaches_marketplace(page, e2e_config, test_buyer):
    """Login slice: seeded buyer → marketplace (skips register and checkout)."""
    LoginPage(page, e2e_config).open(next_path="/mybook/marketplace")
    LoginPage(page, e2e_config).login(test_buyer)
    expect(page).to_have_url(_MARKETPLACE_URL)


@pytest.mark.auth
@pytest.mark.buyer
def test_buyer_login_via_workflow(page, context, e2e_config, test_buyer):
    """Same slice using BuyerWorkflow.login() helper."""
    BuyerWorkflow(page, context, e2e_config).login(test_buyer, next_path="/mybook/marketplace")
    expect(page).to_have_url(_MARKETPLACE_URL)
