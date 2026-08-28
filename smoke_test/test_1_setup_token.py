"""Setup login for smoke test for cookidoo-api."""

from cookidoo_api.cookidoo import Cookidoo
from smoke_test.conftest import TOKEN_FILE


class TestLoginAndValidation:
    """Test login and validation."""

    async def test_cookidoo_login(self, cookidoo_no_auth: Cookidoo) -> None:
        """Test cookidoo login via OAuth2 flow and save the token."""
        await cookidoo_no_auth.login()
        assert cookidoo_no_auth._logged_in
        cookidoo_no_auth.save_token(TOKEN_FILE)
