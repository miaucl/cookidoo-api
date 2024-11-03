"""Setup token for smoke test for cookidoo-api."""

import asyncio

from cookidoo_api.cookidoo import Cookidoo
from smoke_test.conftest import save_token


class TestLoginAndValidation:
    """Test login and validation."""

    async def test_cookidoo_login(self, cookidoo_no_auth: Cookidoo) -> None:
        """Test cookidoo validation of the token or login otherwise."""
        await cookidoo_no_auth.login()  # Should login
        await asyncio.sleep(3)
        expires_in_login = cookidoo_no_auth.expires_in
        await cookidoo_no_auth.refresh_token()  # Should refresh
        expires_in_refesh = cookidoo_no_auth.expires_in
        assert expires_in_refesh > expires_in_login
        if auth_data := cookidoo_no_auth.auth_data:
            save_token(auth_data)
