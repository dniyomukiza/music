"""Reader account management (standalone slice)."""
import pytest

from e2e.workflows.buyer import BuyerWorkflow


@pytest.mark.account
@pytest.mark.buyer
def test_buyer_updates_account_profile(page, context, e2e_config, test_buyer):
    wf = BuyerWorkflow(page, context, e2e_config)
    wf.login(test_buyer, next_path="/mybook/account")
    wf.update_account(
        first_name="E2EUpdated",
        last_name="Reader",
        email=test_buyer.email,
    )
    from e2e.pages.reader_account import ReaderAccountPage

    ReaderAccountPage(page, e2e_config).expect_name_fields("E2EUpdated", "Reader")
