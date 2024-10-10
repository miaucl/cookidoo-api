"""Setup cookies for smoke test for cookidoo-api."""

from dotenv import load_dotenv

from cookidoo_api.cookidoo import Cookidoo
from smoke_test.conftest import save_cookies

load_dotenv()


class TestLoginAndValidation:
    """Test login and validation."""

    async def test_cookidoo_login(self, cookidoo: Cookidoo) -> None:
        """Test cookidoo validation of the token or login otherwise."""
        await cookidoo.login()  # Should login
        await cookidoo.login()  # Should only validate
        save_cookies(cookidoo.cookies)
