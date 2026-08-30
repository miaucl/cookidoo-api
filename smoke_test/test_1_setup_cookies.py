"""Setup login (cookie-session fallback) for smoke test for cookidoo-api."""

from cookidoo_api.cookidoo import Cookidoo
from smoke_test.conftest import COOKIE_FILE


class TestLoginAndValidation:
    """Test login and validation."""

    async def test_cookidoo_login(self, cookidoo_no_auth_cookie: Cookidoo) -> None:
        """Test cookidoo login via the cookie-session fallback flow and save the cookies."""
        await cookidoo_no_auth_cookie.login()
        assert cookidoo_no_auth_cookie._logged_in
        cookidoo_no_auth_cookie.save_cookies(COOKIE_FILE)
