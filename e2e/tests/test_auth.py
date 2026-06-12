"""Auth smoke tests — register and login (partial workflow)."""
import re
from urllib.parse import urlparse

import pytest
from playwright.sync_api import expect

from e2e.pages.auth import LoginPage, RegisterPage
from e2e.support.user_factory import build_test_user, resolve_user_id
from e2e.workflows.author import AuthorWorkflow

_SETUP_PROFILE_PATH = "/mybook/setup-profile"


@pytest.mark.smoke
@pytest.mark.auth
def test_author_can_register_and_login(page, e2e_config, worker_id, user_registry):
    user = build_test_user(e2e_config, role="author", worker_id=worker_id, label="auth")
    RegisterPage(page, e2e_config).open()
    RegisterPage(page, e2e_config).register(user)

    # After register, app sends user to check-email; login works without confirm
    LoginPage(page, e2e_config).open(next_path=_SETUP_PROFILE_PATH)
    LoginPage(page, e2e_config).login(user)
    # Path-only check — avoid false pass when still on /routes1/login?next=/mybook/...
    assert urlparse(page.url).path == _SETUP_PROFILE_PATH, (
        f"Expected setup-profile after login, got path={urlparse(page.url).path!r} url={page.url!r}"
    )

    uid = resolve_user_id(user.username, email=user.email)
    assert uid is not None
    user_registry.track_id(uid)


@pytest.mark.smoke
@pytest.mark.auth
def test_seeded_author_reaches_setup_profile(page, e2e_config, test_author):
    AuthorWorkflow(page, e2e_config).login(test_author)
    page.goto(f"{e2e_config.base_url}/mybook/setup-profile")
    page.wait_for_selector("#profileSetupForm")
