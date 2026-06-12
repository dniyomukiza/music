"""Registration and login page objects."""
from __future__ import annotations

import re

from playwright.sync_api import Page, expect

from e2e.config import E2EConfig
from e2e.pages.base import BasePage
from e2e.support.user_factory import TestUser


class RegisterPage(BasePage):
    PATH = "/routes1/register"

    def open(self, next_path: str | None = None) -> None:
        path = self.PATH
        if next_path:
            path = f"{path}?next={next_path}"
        self.goto(path)

    def register(self, user: TestUser) -> None:
        self.page.fill("#fname", user.first_name)
        self.page.fill("#lname", user.last_name)
        self.page.fill("#email", user.email)
        self.page.fill("#username", user.username)
        self.page.fill("#password", user.password)
        self.page.select_option("#role", value=user.role)
        with self.page.expect_navigation(
            url=re.compile(r"/routes1/check_email"),
            timeout=self.cfg.navigation_timeout_ms,
        ):
            self.page.click('input[type="submit"].btn')


class LoginPage(BasePage):
    PATH = "/routes1/login"

    def open(self, next_path: str | None = None) -> None:
        path = self.PATH
        if next_path:
            path = f"{path}?next={next_path}"
        self.goto(path)

    def login(self, user: TestUser) -> None:
        self.page.fill('input[name="username"]', user.username)
        self.page.fill('input[name="password"]', user.password)
        self.page.click('input[type="submit"].btn')
        self.page.wait_for_load_state("networkidle")

    def login_expect_redirect(self, user: TestUser, url_fragment: str) -> None:
        self.login(user)
        expect(self.page).to_have_url(re.compile(re.escape(url_fragment)), timeout=self.cfg.navigation_timeout_ms)
