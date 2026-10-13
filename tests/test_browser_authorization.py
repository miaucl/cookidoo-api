"""External-agent OAuth handoff without collecting account credentials."""

import asyncio
import base64
from collections.abc import AsyncGenerator, Generator
import hashlib
import re
from typing import Any
from unittest.mock import patch
from urllib.parse import parse_qs, urlencode, urlparse

from aiohttp import ClientError, ClientSession
from aioresponses import CallbackResult, aioresponses
import pytest
from yarl import URL

from cookidoo_api import (
    Cookidoo,
    CookidooAuthData,
    CookidooAuthException,
    CookidooConfig,
    CookidooRequestException,
)
from cookidoo_api.const import CIAM_BASE_URL, OIDC_DISCOVERY_URL

TOKEN_ENDPOINT = CIAM_BASE_URL + "/token-srv/token"
AUTHORIZATION_ENDPOINT = CIAM_BASE_URL + "/authz-srv/authz"
REDIRECT_URI = "test.cookidoo.api://code-grant"
TOKEN_PAYLOAD = {
    "access_token": "synthetic-access",
    "refresh_token": "synthetic-refresh",
    "expires_in": 3600,
}


@pytest.fixture
async def client() -> AsyncGenerator[Cookidoo]:
    """Use empty account credentials and a registered test client identifier."""
    async with ClientSession() as session:
        yield Cookidoo(
            session,
            CookidooConfig(
                email="",
                password="",
                client_id="browser-test",
                redirect_uri=REDIRECT_URI,
            ),
        )


@pytest.fixture
def mocked() -> Generator[aioresponses]:
    """Intercept all HTTP; only OIDC discovery is registered initially."""
    with aioresponses() as responses:
        responses.get(
            OIDC_DISCOVERY_URL,
            payload={
                "authorization_endpoint": AUTHORIZATION_ENDPOINT,
                "token_endpoint": TOKEN_ENDPOINT,
            },
            repeat=True,
        )
        yield responses


def callback(url: str, **overrides: str) -> str:
    """Model the provider's redirect with the authorization request's state."""
    params = {
        "code": "synthetic-code",
        "state": parse_qs(urlparse(url).query)["state"][0],
    }
    params.update(overrides)
    return REDIRECT_URI + "?" + urlencode(params)


async def test_browser_handoff_pkce_and_token_callback(
    client: Cookidoo,
    mocked: aioresponses,
) -> None:
    """Only discovery and one code exchange occur, with correct PKCE binding."""
    updates: list[CookidooAuthData] = []
    client.on_auth_data_update = updates.append
    url = await client.begin_login()
    params = parse_qs(urlparse(url).query)
    assert params["code_challenge_method"] == ["S256"]
    assert params["redirect_uri"] == [REDIRECT_URI]
    assert params["client_id"] == ["browser-test"]
    assert "password" not in params

    def token_response(_url: URL, **kwargs: Any) -> CallbackResult:
        data = kwargs["data"]
        challenge = (
            base64.urlsafe_b64encode(
                hashlib.sha256(data["code_verifier"].encode()).digest()
            )
            .rstrip(b"=")
            .decode()
        )
        assert params["code_challenge"] == [challenge]
        assert data["code"] == "synthetic-code"
        assert data["redirect_uri"] == REDIRECT_URI
        assert data["client_id"] == "browser-test"
        assert "client_secret" not in data
        assert "password" not in data
        return CallbackResult(payload=TOKEN_PAYLOAD)

    mocked.post(TOKEN_ENDPOINT, callback=token_response)
    await client.complete_login(callback(url))

    assert client.auth_data is not None
    assert client.auth_data.access_token == "synthetic-access"
    assert client.auth_data.refresh_token == "synthetic-refresh"
    assert len(updates) == 1
    assert len(mocked.requests) == 2
    with pytest.raises(CookidooAuthException, match="No browser login"):
        await client.complete_login(callback(url))


@pytest.mark.parametrize(
    "bad_callback",
    [
        "https://example.invalid/callback?code=synthetic-code&state={state}",
        REDIRECT_URI + "/other?code=synthetic-code&state={state}",
        REDIRECT_URI + "?code=synthetic-code",
        REDIRECT_URI + "?code=synthetic-code&state=wrong",
        REDIRECT_URI + "?code=synthetic-code&state={state}&state=other",
        REDIRECT_URI + "?code=one&code=two&state={state}",
        REDIRECT_URI + "?code=&state={state}",
        REDIRECT_URI + "?code=synthetic-code&state={state}#fragment",
        REDIRECT_URI + "?error=denied&error_description=SENSITIVE&state={state}",
        REDIRECT_URI + "?state={state}",
    ],
)
async def test_invalid_callback_consumes_state_without_sending_a_code(
    client: Cookidoo,
    mocked: aioresponses,
    bad_callback: str,
) -> None:
    """Wrong target, denied login, missing or duplicate values cannot authorize."""
    url = await client.begin_login()
    state = parse_qs(urlparse(url).query)["state"][0]
    with pytest.raises(CookidooAuthException) as caught:
        await client.complete_login(bad_callback.format(state=state))
    assert "SENSITIVE" not in str(caught.value)
    assert client.auth_data is None
    assert len(mocked.requests) == 1
    with pytest.raises(CookidooAuthException, match="No browser login"):
        await client.complete_login(callback(url))


async def test_restart_invalidates_old_state(
    client: Cookidoo,
    mocked: aioresponses,
) -> None:
    """Each attempt has fresh state and PKCE; an older callback is refused."""
    first = await client.begin_login()
    second = await client.begin_login()
    p1, p2 = parse_qs(urlparse(first).query), parse_qs(urlparse(second).query)
    assert p1["state"] != p2["state"]
    assert p1["code_challenge"] != p2["code_challenge"]
    with pytest.raises(CookidooAuthException, match="state mismatch"):
        await client.complete_login(callback(first))
    assert len(mocked.requests) == 1


async def test_cancel_and_expiry_preserve_existing_tokens(
    client: Cookidoo,
    mocked: aioresponses,
) -> None:
    """Neither abandoning an attempt nor its expiration logs out a session."""
    old = CookidooAuthData("existing-access", "existing-refresh", 9999999999.0)
    client.apply_auth_data(old)
    with patch("cookidoo_api.cookidoo.time.monotonic", return_value=100):
        url = await client.begin_login()
    with (
        patch("cookidoo_api.cookidoo.time.monotonic", return_value=400),
        pytest.raises(CookidooAuthException, match="expired"),
    ):
        await client.complete_login(callback(url))
    assert client.auth_data == old
    url = await client.begin_login()
    client.cancel_login()
    client.cancel_login()
    with pytest.raises(CookidooAuthException, match="No browser login"):
        await client.complete_login(callback(url))
    assert client.auth_data == old
    assert len(mocked.requests) == 1


async def test_client_configuration_change_cannot_redirect_the_exchange(
    client: Cookidoo,
    mocked: aioresponses,
) -> None:
    """A handoff remains bound to the client and redirect it started with."""
    url = await client.begin_login()
    client._cfg.client_id = "different-client"
    with pytest.raises(CookidooAuthException, match="configuration changed"):
        await client.complete_login(callback(url))
    assert len(mocked.requests) == 1


@pytest.mark.parametrize("error", [TimeoutError(), ClientError(), None])
async def test_failed_exchange_is_not_retried(
    client: Cookidoo,
    mocked: aioresponses,
    error: Exception | None,
) -> None:
    """An uncertain or rejected exchange needs a newly authorized attempt."""
    url = await client.begin_login()
    if error is None:
        mocked.post(TOKEN_ENDPOINT, status=400)
    else:
        mocked.post(TOKEN_ENDPOINT, exception=error)
    with pytest.raises(
        CookidooAuthException if error is None else CookidooRequestException
    ):
        await client.complete_login(callback(url))
    with pytest.raises(CookidooAuthException, match="No browser login"):
        await client.complete_login(callback(url))
    assert len(mocked.requests[("POST", URL(TOKEN_ENDPOINT))]) == 1


async def test_bearer_refresh_after_external_login(
    client: Cookidoo,
    mocked: aioresponses,
) -> None:
    """The handoff produces the normal renewable API session."""
    url = await client.begin_login()
    mocked.post(TOKEN_ENDPOINT, payload=TOKEN_PAYLOAD)
    await client.complete_login(callback(url))
    mocked.post(
        TOKEN_ENDPOINT, payload={**TOKEN_PAYLOAD, "access_token": "refreshed-access"}
    )
    await client.refresh()
    assert client.auth_data is not None
    assert client.auth_data.access_token == "refreshed-access"


async def test_password_login_invalidates_pending_browser_callback(
    client: Cookidoo,
    mocked: aioresponses,
) -> None:
    """Switching login mechanisms cannot later reuse the old browser attempt."""
    url = await client.begin_login()
    mocked.get(re.compile(AUTHORIZATION_ENDPOINT + ".*"), status=403)
    with pytest.raises(CookidooAuthException):
        await client.login()
    with pytest.raises(CookidooAuthException, match="No browser login"):
        await client.complete_login(callback(url))


@pytest.mark.parametrize("error", [TimeoutError(), ClientError()])
async def test_failed_discovery_does_not_leave_a_pending_attempt(
    client: Cookidoo,
    mocked: aioresponses,
    error: Exception,
) -> None:
    """Discovery failures use the library's request exception surface."""
    mocked.clear()
    mocked.get(OIDC_DISCOVERY_URL, exception=error)
    with pytest.raises(CookidooRequestException):
        await client.begin_login()
    with pytest.raises(CookidooAuthException, match="No browser login"):
        await client.complete_login(REDIRECT_URI)


@pytest.mark.parametrize("endpoint_key", ["authorization_endpoint", "token_endpoint"])
async def test_discovery_cannot_send_authorization_to_another_origin(
    client: Cookidoo,
    mocked: aioresponses,
    endpoint_key: str,
) -> None:
    """An unexpected OIDC endpoint never creates a pending browser login."""
    mocked.clear()
    discovery = {
        "authorization_endpoint": AUTHORIZATION_ENDPOINT,
        "token_endpoint": TOKEN_ENDPOINT,
    }
    discovery[endpoint_key] = "https://example.invalid/oauth"
    mocked.get(OIDC_DISCOVERY_URL, payload=discovery)
    with pytest.raises(CookidooAuthException):
        await client.begin_login()
    with pytest.raises(CookidooAuthException, match="No browser login"):
        await client.complete_login(REDIRECT_URI)


async def test_cancel_during_discovery_cannot_create_a_late_attempt(
    client: Cookidoo,
    mocked: aioresponses,
) -> None:
    """A cancelled in-flight start cannot reactivate authorization afterwards."""
    started, release = asyncio.Event(), asyncio.Event()

    async def discovery() -> dict[str, str]:
        started.set()
        await release.wait()
        return {
            "authorization_endpoint": AUTHORIZATION_ENDPOINT,
            "token_endpoint": TOKEN_ENDPOINT,
        }

    with patch.object(client, "_discovery", side_effect=discovery):
        task = asyncio.create_task(client.begin_login())
        await started.wait()
        client.cancel_login()
        release.set()
        with pytest.raises(CookidooAuthException, match="cancelled or superseded"):
            await task
    with pytest.raises(CookidooAuthException, match="No browser login"):
        await client.complete_login(REDIRECT_URI)
    assert not mocked.requests


async def test_cancel_during_exchange_never_adopts_late_tokens(
    client: Cookidoo,
    mocked: aioresponses,
) -> None:
    """Cancelling a pending exchange leaves the previous authenticated session intact."""
    old = CookidooAuthData("existing-access", "existing-refresh", 9999999999.0)
    client.apply_auth_data(old)
    url = await client.begin_login()
    started, release = asyncio.Event(), asyncio.Event()

    async def token_response(_url: URL, **_kwargs: Any) -> CallbackResult:
        started.set()
        await release.wait()
        return CallbackResult(payload=TOKEN_PAYLOAD)

    mocked.post(TOKEN_ENDPOINT, callback=token_response)
    task = asyncio.create_task(client.complete_login(callback(url)))
    await started.wait()
    client.cancel_login()
    release.set()
    with pytest.raises(CookidooAuthException):
        await task
    assert client.auth_data == old
    assert len(mocked.requests[("POST", URL(TOKEN_ENDPOINT))]) == 1
