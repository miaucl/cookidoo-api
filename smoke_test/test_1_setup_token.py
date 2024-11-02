"""Setup token for smoke test for cookidoo-api."""

import asyncio

from cookidoo_api.cookidoo import Cookidoo


class TestLoginAndValidation:
    """Test login and validation."""

    async def test_cookidoo_login(self, cookidoo: Cookidoo) -> None:
        """Test cookidoo validation of the token or login otherwise."""
        await cookidoo.login()  # Should login
        await asyncio.sleep(3)
        expires_in_login = cookidoo.expires_in
        await cookidoo.refresh_token()  # Should refresh
        expires_in_refesh = cookidoo.expires_in
        assert expires_in_refesh > expires_in_login
