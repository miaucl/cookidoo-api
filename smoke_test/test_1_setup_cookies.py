"""Setup cookies for smoke test for cookidoo-api."""

from cookidoo_api.cookidoo import Cookidoo
from smoke_test.conftest import save_cookies


class TestLoginAndValidation:
    """Test login and validation."""

    async def test_cookidoo_login(self, cookidoo: Cookidoo) -> None:
        """Test cookidoo validation of the token or login otherwise."""
        await cookidoo.check_browser()  # Should login
        await cookidoo.login()  # Should login
        await cookidoo.login()  # Should only validate
        save_cookies(cookidoo.cookies)
