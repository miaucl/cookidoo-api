"""Malformed OAuth payloads must not expose credentials in exception output."""

import traceback

from aiohttp import ClientSession
import pytest

from cookidoo_api import Cookidoo, CookidooAuthException


@pytest.mark.parametrize(
    "payload",
    [
        {"refresh_token": "SENSITIVE_REFRESH", "id_token": "SENSITIVE_ID"},
        {
            "access_token": "SENSITIVE_ACCESS",
            "refresh_token": "SENSITIVE_REFRESH",
            "expires_in": "SENSITIVE_EXPIRY",
        },
    ],
)
async def test_malformed_token_response_does_not_leak_payload_or_exception_cause(
    payload: dict[str, object],
) -> None:
    """Exception messages and formatted tracebacks exclude upstream values."""
    async with ClientSession() as session:
        client = Cookidoo(session)
        with pytest.raises(CookidooAuthException) as caught:
            client._apply_tokens(payload)

        assert str(caught.value) == "Unexpected token response."
        rendered = "".join(traceback.format_exception(caught.value))
        assert "SENSITIVE_" not in rendered
        assert client.auth_data is None
