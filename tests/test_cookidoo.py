"""Unit tests for cookidoo-api."""

import asyncio
from collections.abc import Callable
from datetime import datetime
from http import HTTPStatus
import pathlib
import re
from typing import Any

from aiohttp import ClientError, ClientSession
from aioresponses import CallbackResult, aioresponses
from dotenv import load_dotenv
import pytest
from yarl import URL

from cookidoo_api import cooking_activity_from_push
from cookidoo_api.const import (
    CIAM_LOGIN_SRV_URL,
    OAUTH_CLIENT_ID,
    OAUTH_REDIRECT_URI,
    OIDC_DISCOVERY_URL,
)
from cookidoo_api.cookidoo import Cookidoo
from cookidoo_api.exceptions import (
    CookidooAuthException,
    CookidooConfigException,
    CookidooException,
    CookidooParseException,
    CookidooRequestException,
)
from cookidoo_api.helpers import get_localization_options
from cookidoo_api.types import (
    CookidooAdditionalItem,
    CookidooAuthData,
    CookidooConfig,
    CookidooCookState,
    CookidooIngredientItem,
    CookidooSearchResult,
    ThermomixMachineType,
)
from tests.conftest import TEST_CLIENT_ID, TEST_REDIRECT_URI
from tests.responses import (
    COOKIDOO_TEST_LOGIN_PAGE_HTML,
    COOKIDOO_TEST_OIDC_DISCOVERY,
    COOKIDOO_TEST_PUSH_COOKING_ACTIVITY,
    COOKIDOO_TEST_REFRESHED_TOKEN_RESPONSE,
    COOKIDOO_TEST_RESPONSE_ACTIVE_SUBSCRIPTION,
    COOKIDOO_TEST_RESPONSE_ADD_ADDITIONAL_ITEMS,
    COOKIDOO_TEST_RESPONSE_ADD_CUSTOM_COLLECTION,
    COOKIDOO_TEST_RESPONSE_ADD_CUSTOM_RECIPE,
    COOKIDOO_TEST_RESPONSE_ADD_CUSTOM_RECIPES_TO_CALENDAR,
    COOKIDOO_TEST_RESPONSE_ADD_INGREDIENTS_FOR_CUSTOM_RECIPES,
    COOKIDOO_TEST_RESPONSE_ADD_INGREDIENTS_FOR_RECIPES,
    COOKIDOO_TEST_RESPONSE_ADD_MANAGED_COLLECTION,
    COOKIDOO_TEST_RESPONSE_ADD_RECIPES_TO_CALENDAR,
    COOKIDOO_TEST_RESPONSE_ADD_RECIPES_TO_CUSTOM_COLLECTION,
    COOKIDOO_TEST_RESPONSE_CALENDAR_WEEK,
    COOKIDOO_TEST_RESPONSE_DEVICES,
    COOKIDOO_TEST_RESPONSE_DEVICES_EMPTY,
    COOKIDOO_TEST_RESPONSE_DEVICES_MULTIPLE,
    COOKIDOO_TEST_RESPONSE_EDIT_ADDITIONAL_ITEMS,
    COOKIDOO_TEST_RESPONSE_EDIT_ADDITIONAL_ITEMS_OWNERSHIP,
    COOKIDOO_TEST_RESPONSE_EDIT_INGREDIENTS_OWNERSHIP,
    COOKIDOO_TEST_RESPONSE_GET_ADDITIONAL_ITEMS,
    COOKIDOO_TEST_RESPONSE_GET_CUSTOM_COLLECTIONS,
    COOKIDOO_TEST_RESPONSE_GET_CUSTOM_RECIPE,
    COOKIDOO_TEST_RESPONSE_GET_INGREDIENTS_FOR_CUSTOM_RECIPES,
    COOKIDOO_TEST_RESPONSE_GET_INGREDIENTS_FOR_RECIPES,
    COOKIDOO_TEST_RESPONSE_GET_MANAGED_COLLECTIONS,
    COOKIDOO_TEST_RESPONSE_GET_RECIPE_DETAILS,
    COOKIDOO_TEST_RESPONSE_GET_SHOPPING_LIST_RECIPES,
    COOKIDOO_TEST_RESPONSE_INACTIVE_SUBSCRIPTION,
    COOKIDOO_TEST_RESPONSE_LIST_CUSTOM_RECIPES,
    COOKIDOO_TEST_RESPONSE_MOBILE_HOME,
    COOKIDOO_TEST_RESPONSE_MONITORED_DEVICES,
    COOKIDOO_TEST_RESPONSE_REMOVE_CUSTOM_RECIPE_FROM_CALENDAR,
    COOKIDOO_TEST_RESPONSE_REMOVE_RECIPE_FROM_CALENDAR,
    COOKIDOO_TEST_RESPONSE_REMOVE_RECIPE_FROM_CUSTOM_COLLECTION,
    COOKIDOO_TEST_RESPONSE_RMI_CONFIG,
    COOKIDOO_TEST_RESPONSE_SEARCH_RECIPES,
    COOKIDOO_TEST_RESPONSE_USER_INFO,
    COOKIDOO_TEST_TOKEN_RESPONSE,
)

load_dotenv()


class TestGetterSetter:
    """Tests for getter and setter."""

    @pytest.mark.parametrize(
        ("country", "language", "expected_domain"),
        [
            ("ch", "de-CH", "https://cookidoo.ch"),
            ("de", "de-DE", "https://cookidoo.de"),
            ("ma", "en", "https://cookidoo.international"),
            ("ie", "en-GB", "https://cookidoo.co.uk"),
            ("gb", "en-GB", "https://cookidoo.co.uk"),
        ],
    )
    async def test_api_endpoint(
        self,
        mocked: aioresponses,
        session: ClientSession,
        country: str,
        language: str,
        expected_domain: str,
    ) -> None:
        """Test api endpoint for different localizations."""
        cookidoo = Cookidoo(
            session,
            cfg=CookidooConfig(
                localization=(
                    await get_localization_options(country=country, language=language)
                )[0],
            ),
        )

        assert str(cookidoo.api_endpoint) == expected_domain

    async def test_localization(self, cookidoo: Cookidoo) -> None:
        """Test localization property."""
        loc = cookidoo.localization
        assert loc.language == "de-CH"
        assert loc.country_code == "ch"


TOKEN_ENDPOINT = "https://ciam.prod.cookidoo.vorwerk-digital.com/token-srv/token"
AUTHZ_RE = re.compile(r".*/authz-srv/authz.*")


class TestLogin:
    """Tests for the OAuth2 authorization-code login flow."""

    @staticmethod
    def _mock_authorize(
        mocked: aioresponses, *, body: str = COOKIDOO_TEST_LOGIN_PAGE_HTML
    ) -> dict[str, str]:
        """Serve the login page and capture the ``state`` the client sent."""
        captured: dict[str, str] = {}

        def _serve(url: URL, **kwargs: Any) -> CallbackResult:
            captured["state"] = url.query["state"]
            return CallbackResult(status=HTTPStatus.OK, body=body)

        mocked.get(AUTHZ_RE, callback=_serve, repeat=True)
        return captured

    @staticmethod
    def _app_redirect(
        captured: dict[str, str], *, code: str | None = "test-code"
    ) -> Callable[..., CallbackResult]:
        """Redirect to the app scheme, echoing the state like CIAM does."""

        def _redirect(url: URL, **kwargs: Any) -> CallbackResult:
            query = [f"code={code}"] if code else []
            query.append(f"state={captured['state']}")
            return CallbackResult(
                status=HTTPStatus.FOUND,
                headers={"Location": f"{TEST_REDIRECT_URI}?{'&'.join(query)}"},
            )

        return _redirect

    @classmethod
    def _mock_login_flow(
        cls,
        mocked: aioresponses,
        *,
        page_body: str = COOKIDOO_TEST_LOGIN_PAGE_HTML,
        code: str | None = "test-code",
    ) -> dict[str, str]:
        mocked.get(OIDC_DISCOVERY_URL, payload=COOKIDOO_TEST_OIDC_DISCOVERY)
        captured = cls._mock_authorize(mocked, body=page_body)
        mocked.post(CIAM_LOGIN_SRV_URL, callback=cls._app_redirect(captured, code=code))
        mocked.post(TOKEN_ENDPOINT, payload=COOKIDOO_TEST_TOKEN_RESPONSE)
        return captured

    async def test_login_success(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test a successful OAuth2 login."""
        self._mock_login_flow(mocked)

        await cookidoo.login()

        assert cookidoo._logged_in
        assert cookidoo.auth_data is not None
        assert cookidoo.auth_data.access_token == "test-access-token"
        assert cookidoo.auth_data.refresh_token == "test-refresh-token"
        assert cookidoo._api_headers["Authorization"] == "Bearer test-access-token"

    async def test_token_request_is_a_public_client_request(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """The code exchange identifies the client without authenticating it.

        CIAM accepts the exchange on the strength of the PKCE ``code_verifier``,
        so no client secret is sent (and none is configurable).
        """
        self._mock_login_flow(mocked)

        await cookidoo.login()

        (_, kwargs) = mocked.requests[("POST", URL(TOKEN_ENDPOINT))][0]
        assert kwargs["data"]["client_id"] == TEST_CLIENT_ID
        assert kwargs["data"]["code_verifier"]
        assert "client_secret" not in kwargs["data"]
        assert "Authorization" not in kwargs["headers"]

    async def test_refresh_is_a_public_client_request(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """The refresh grant identifies the client the same way."""
        mocked.get(OIDC_DISCOVERY_URL, payload=COOKIDOO_TEST_OIDC_DISCOVERY)
        mocked.post(TOKEN_ENDPOINT, payload=COOKIDOO_TEST_TOKEN_RESPONSE)
        cookidoo.apply_auth_data(CookidooAuthData("old", "test-refresh-token", 0.0))

        await cookidoo.refresh()

        (_, kwargs) = mocked.requests[("POST", URL(TOKEN_ENDPOINT))][0]
        assert kwargs["data"]["client_id"] == TEST_CLIENT_ID
        assert "client_secret" not in kwargs["data"]
        assert "Authorization" not in kwargs["headers"]

    async def test_login_page_unreachable(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test login when the authorize/login page returns an error."""
        mocked.get(OIDC_DISCOVERY_URL, payload=COOKIDOO_TEST_OIDC_DISCOVERY)
        mocked.get(AUTHZ_RE, status=HTTPStatus.SERVICE_UNAVAILABLE)

        with pytest.raises(CookidooAuthException, match="could not reach login page"):
            await cookidoo.login()

    async def test_login_page_parse_error(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test login when requestId cannot be extracted."""
        mocked.get(OIDC_DISCOVERY_URL, payload=COOKIDOO_TEST_OIDC_DISCOVERY)
        mocked.get(
            AUTHZ_RE,
            status=HTTPStatus.OK,
            body="<html><body>No form here</body></html>",
        )

        with pytest.raises(CookidooParseException, match="could not extract requestId"):
            await cookidoo.login()

    async def test_login_invalid_credentials(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Invalid credentials yield no authorization code."""
        mocked.get(OIDC_DISCOVERY_URL, payload=COOKIDOO_TEST_OIDC_DISCOVERY)
        mocked.get(AUTHZ_RE, status=HTTPStatus.OK, body=COOKIDOO_TEST_LOGIN_PAGE_HTML)
        # The login service replies 200 (re-renders the form) instead of redirecting.
        mocked.post(CIAM_LOGIN_SRV_URL, status=HTTPStatus.OK)

        with pytest.raises(CookidooAuthException, match="invalid credentials"):
            await cookidoo.login()

    async def test_login_follows_intermediate_redirects(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Redirects before the app scheme are followed to capture the code."""
        mocked.get(OIDC_DISCOVERY_URL, payload=COOKIDOO_TEST_OIDC_DISCOVERY)
        captured = self._mock_authorize(mocked)
        interstitial = (
            "https://ciam.prod.cookidoo.vorwerk-digital.com/login-srv/continue"
        )
        mocked.post(
            CIAM_LOGIN_SRV_URL,
            status=HTTPStatus.FOUND,
            headers={"Location": interstitial},
        )
        mocked.get(interstitial, callback=self._app_redirect(captured))
        mocked.post(TOKEN_ENDPOINT, payload=COOKIDOO_TEST_TOKEN_RESPONSE)

        await cookidoo.login()

        assert cookidoo._logged_in

    async def test_login_refuses_redirect_off_the_auth_host(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """A redirect leaving the CIAM origin is refused instead of followed."""
        mocked.get(OIDC_DISCOVERY_URL, payload=COOKIDOO_TEST_OIDC_DISCOVERY)
        self._mock_authorize(mocked)
        mocked.post(
            CIAM_LOGIN_SRV_URL,
            status=HTTPStatus.FOUND,
            headers={"Location": "https://evil.example/login-srv/continue"},
        )

        with pytest.raises(
            CookidooAuthException, match="redirected off the authentication host"
        ):
            await cookidoo.login()

    async def test_login_state_mismatch(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """A state that does not match the one sent aborts the login."""
        mocked.get(OIDC_DISCOVERY_URL, payload=COOKIDOO_TEST_OIDC_DISCOVERY)
        self._mock_authorize(mocked)
        mocked.post(
            CIAM_LOGIN_SRV_URL,
            status=HTTPStatus.FOUND,
            headers={"Location": f"{TEST_REDIRECT_URI}?code=test-code&state=tampered"},
        )

        with pytest.raises(CookidooAuthException, match="state mismatch"):
            await cookidoo.login()

    async def test_login_state_missing(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """A callback that omits the state entirely counts as a mismatch."""
        mocked.get(OIDC_DISCOVERY_URL, payload=COOKIDOO_TEST_OIDC_DISCOVERY)
        self._mock_authorize(mocked)
        mocked.post(
            CIAM_LOGIN_SRV_URL,
            status=HTTPStatus.FOUND,
            headers={"Location": f"{TEST_REDIRECT_URI}?code=test-code"},
        )

        with pytest.raises(CookidooAuthException, match="state mismatch"):
            await cookidoo.login()

    async def test_login_sends_the_state_it_verifies(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """The state accepted on the callback is the one the client sent."""
        mocked.get(OIDC_DISCOVERY_URL, payload=COOKIDOO_TEST_OIDC_DISCOVERY)
        captured = self._mock_authorize(mocked)
        mocked.post(CIAM_LOGIN_SRV_URL, callback=self._app_redirect(captured))
        mocked.post(TOKEN_ENDPOINT, payload=COOKIDOO_TEST_TOKEN_RESPONSE)

        await cookidoo.login()

        assert captured["state"]
        assert cookidoo._logged_in

    async def test_login_redirect_loop(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """An endless redirect chain gives up instead of looping forever."""
        mocked.get(OIDC_DISCOVERY_URL, payload=COOKIDOO_TEST_OIDC_DISCOVERY)
        mocked.get(AUTHZ_RE, status=HTTPStatus.OK, body=COOKIDOO_TEST_LOGIN_PAGE_HTML)
        loop_url = "https://ciam.prod.cookidoo.vorwerk-digital.com/login-srv/loop"
        mocked.post(
            CIAM_LOGIN_SRV_URL,
            status=HTTPStatus.FOUND,
            headers={"Location": loop_url},
        )
        mocked.get(
            re.compile(r".*/login-srv/loop.*"),
            status=HTTPStatus.FOUND,
            headers={"Location": loop_url},
            repeat=True,
        )

        with pytest.raises(CookidooAuthException, match="invalid credentials"):
            await cookidoo.login()

    async def test_login_token_exchange_failure(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """A rejected code exchange surfaces as an auth exception."""
        mocked.get(OIDC_DISCOVERY_URL, payload=COOKIDOO_TEST_OIDC_DISCOVERY)
        captured = self._mock_authorize(mocked)
        mocked.post(CIAM_LOGIN_SRV_URL, callback=self._app_redirect(captured))
        mocked.post(TOKEN_ENDPOINT, status=HTTPStatus.BAD_REQUEST)

        with pytest.raises(CookidooAuthException, match="Token exchange failed"):
            await cookidoo.login()

    async def test_login_unexpected_token_response(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """A token response without an access token surfaces as an auth exception."""
        mocked.get(OIDC_DISCOVERY_URL, payload=COOKIDOO_TEST_OIDC_DISCOVERY)
        captured = self._mock_authorize(mocked)
        mocked.post(CIAM_LOGIN_SRV_URL, callback=self._app_redirect(captured))
        mocked.post(TOKEN_ENDPOINT, payload={"token_type": "Bearer"})

        with pytest.raises(CookidooAuthException, match="Unexpected token response"):
            await cookidoo.login()

    async def test_discovery_is_cached(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """The OIDC discovery document is only fetched once."""
        captured = self._mock_login_flow(mocked)

        await cookidoo.login()
        # A second login must not hit the discovery endpoint again, it is only
        # mocked once and a second request would fail.
        mocked.post(CIAM_LOGIN_SRV_URL, callback=self._app_redirect(captured))
        mocked.post(TOKEN_ENDPOINT, payload=COOKIDOO_TEST_TOKEN_RESPONSE)

        await cookidoo.login()

        assert cookidoo._logged_in

    def test_default_oauth_client_is_the_public_mobile_client(self) -> None:
        """The client identifiers default to the app's public ones."""
        cfg = CookidooConfig()

        assert cfg.client_id == OAUTH_CLIENT_ID
        assert cfg.redirect_uri == OAUTH_REDIRECT_URI
        assert not hasattr(cfg, "client_secret")

    @pytest.mark.parametrize(
        ("client_id", "redirect_uri", "expected"),
        [
            ("", TEST_REDIRECT_URI, "client_id"),
            (TEST_CLIENT_ID, "", "redirect_uri"),
            ("", "", "client_id, redirect_uri"),
        ],
    )
    async def test_login_with_blanked_client_config(
        self,
        session: ClientSession,
        client_id: str,
        redirect_uri: str,
        expected: str,
    ) -> None:
        """Overriding an identifier with an empty value is rejected early."""
        cookidoo = Cookidoo(
            session,
            cfg=CookidooConfig(client_id=client_id, redirect_uri=redirect_uri),
        )

        with pytest.raises(CookidooConfigException, match=expected):
            await cookidoo.login()

    async def test_refresh_with_blanked_client_config(
        self, session: ClientSession
    ) -> None:
        """Refreshing a restored token validates the client config too."""
        cookidoo = Cookidoo(session, cfg=CookidooConfig(client_id=""))
        cookidoo.apply_auth_data(CookidooAuthData("old", "ref", 9999999999.0))

        with pytest.raises(
            CookidooConfigException, match="Missing OAuth2 client configuration"
        ):
            await cookidoo.refresh()

    @pytest.mark.parametrize(
        "exception",
        [
            TimeoutError,
            ClientError,
        ],
    )
    async def test_request_exceptions(
        self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception
    ) -> None:
        """Test that transport exceptions surface as request exceptions."""
        mocked.get(OIDC_DISCOVERY_URL, payload=COOKIDOO_TEST_OIDC_DISCOVERY)
        mocked.get(AUTHZ_RE, exception=exception)

        with pytest.raises(CookidooRequestException):
            await cookidoo.login()


class TestTokenPersistenceAndRefresh:
    """Tests for token persistence and refresh."""

    async def test_save_and_load_token(
        self, cookidoo: Cookidoo, tmp_path: pathlib.Path
    ) -> None:
        """Test saving and restoring tokens across instances."""
        cookidoo.apply_auth_data(CookidooAuthData("acc", "ref", 9999999999.0))
        token_file = tmp_path / "token.json"
        cookidoo.save_token(token_file)
        assert token_file.exists()

        fresh = Cookidoo(cookidoo._session)
        fresh.load_token(token_file)
        assert fresh._logged_in
        assert fresh.auth_data is not None
        assert fresh.auth_data.access_token == "acc"
        assert fresh.auth_data.refresh_token == "ref"

    async def test_save_token_not_logged_in(
        self, cookidoo: Cookidoo, tmp_path: pathlib.Path
    ) -> None:
        """Saving without a login raises."""
        with pytest.raises(CookidooConfigException, match="not logged in"):
            cookidoo.save_token(tmp_path / "token.json")

    async def test_load_token_missing_file(self, cookidoo: Cookidoo) -> None:
        """Loading a missing token file raises."""
        with pytest.raises(CookidooConfigException, match="Cannot load token"):
            cookidoo.load_token("/nonexistent/path/token.json")

    async def test_refresh(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test refreshing the access token."""
        cookidoo.apply_auth_data(CookidooAuthData("old", "ref", 9999999999.0))
        mocked.get(OIDC_DISCOVERY_URL, payload=COOKIDOO_TEST_OIDC_DISCOVERY)
        mocked.post(TOKEN_ENDPOINT, payload=COOKIDOO_TEST_REFRESHED_TOKEN_RESPONSE)

        await cookidoo.refresh()

        assert cookidoo.auth_data is not None
        assert cookidoo.auth_data.access_token == "refreshed-access-token"
        assert cookidoo.auth_data.refresh_token == "refreshed-refresh-token"

    async def test_refresh_without_login(self, cookidoo: Cookidoo) -> None:
        """Refreshing without a refresh token raises."""
        with pytest.raises(CookidooAuthException, match="no refresh token available"):
            await cookidoo.refresh()

    async def test_refresh_rejected(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """A rejected refresh surfaces as an auth exception."""
        cookidoo.apply_auth_data(CookidooAuthData("old", "ref", 9999999999.0))
        mocked.get(OIDC_DISCOVERY_URL, payload=COOKIDOO_TEST_OIDC_DISCOVERY)
        mocked.post(TOKEN_ENDPOINT, status=HTTPStatus.UNAUTHORIZED)

        with pytest.raises(CookidooAuthException, match="Token refresh failed"):
            await cookidoo.refresh()

    async def test_refresh_request_exception(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """A transport error during refresh surfaces as a request exception."""
        cookidoo.apply_auth_data(CookidooAuthData("old", "ref", 9999999999.0))
        mocked.get(OIDC_DISCOVERY_URL, payload=COOKIDOO_TEST_OIDC_DISCOVERY)
        mocked.post(TOKEN_ENDPOINT, exception=ClientError())

        with pytest.raises(CookidooRequestException, match="Token refresh failed"):
            await cookidoo.refresh()

    async def test_no_refresh_on_valid_token(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """A still valid access token is used as is, without a refresh."""
        cookidoo.apply_auth_data(CookidooAuthData("valid", "ref", 9999999999.0))
        mocked.get(
            "https://cookidoo.ch/community/profile/de-CH",
            payload=COOKIDOO_TEST_RESPONSE_USER_INFO,
            status=HTTPStatus.OK,
        )

        await cookidoo.get_user_info()

        # No token endpoint was mocked, so a refresh would have failed.
        assert cookidoo.auth_data is not None
        assert cookidoo.auth_data.access_token == "valid"

    async def test_auto_refresh_on_expired_token(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """An expired access token is refreshed automatically before a request."""
        cookidoo.apply_auth_data(CookidooAuthData("expired", "ref", 0.0))
        mocked.get(OIDC_DISCOVERY_URL, payload=COOKIDOO_TEST_OIDC_DISCOVERY)
        mocked.post(TOKEN_ENDPOINT, payload=COOKIDOO_TEST_REFRESHED_TOKEN_RESPONSE)
        mocked.get(
            "https://cookidoo.ch/community/profile/de-CH",
            payload=COOKIDOO_TEST_RESPONSE_USER_INFO,
            status=HTTPStatus.OK,
        )

        await cookidoo.get_user_info()

        assert cookidoo.auth_data is not None
        assert cookidoo.auth_data.access_token == "refreshed-access-token"


class TestGetUserInfo:
    """Tests for get_user_info method."""

    async def test_get_user_info(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for get_user_info."""

        mocked.get(
            "https://cookidoo.ch/community/profile/de-CH",
            payload=COOKIDOO_TEST_RESPONSE_USER_INFO,
            status=HTTPStatus.OK,
        )

        data = await cookidoo.get_user_info()
        assert data.id == COOKIDOO_TEST_RESPONSE_USER_INFO["id"]
        assert (
            data.username == COOKIDOO_TEST_RESPONSE_USER_INFO["userInfo"]["username"]  # type: ignore[index]
        )
        assert (
            data.description
            == COOKIDOO_TEST_RESPONSE_USER_INFO["userInfo"]["description"]  # type: ignore[index]
        )
        assert (
            data.picture == COOKIDOO_TEST_RESPONSE_USER_INFO["userInfo"]["picture"]  # type: ignore[index]
        )

    @pytest.mark.parametrize(
        "exception",
        [
            TimeoutError,
            ClientError,
        ],
    )
    async def test_request_exception(
        self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception
    ) -> None:
        """Test request exceptions."""

        mocked.get(
            "https://cookidoo.ch/community/profile/de-CH",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.get_user_info()

    async def test_endpoint_discovery_retries_once_and_succeeds(
        self,
        mocked: aioresponses,
        cookidoo: Cookidoo,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A transient discovery failure is retried once and can still succeed."""
        calls = 0

        async def _flaky(*_args: object, **_kwargs: object) -> dict[str, str]:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise CookidooRequestException("boom")
            return {
                "community-profile:user-private-profile": "community/profile/{language}"
            }

        monkeypatch.setattr(
            "cookidoo_api.cookidoo.resolve_endpoint_paths",
            _flaky,
        )
        mocked.get(
            "https://cookidoo.ch/community/profile/de-CH",
            payload=COOKIDOO_TEST_RESPONSE_USER_INFO,
            status=HTTPStatus.OK,
        )

        await cookidoo.get_user_info()

        assert calls == 2
        assert cookidoo._endpoints_resolved
        assert (
            cookidoo._endpoint_overrides["community-profile:user-private-profile"]
            == "community/profile/{language}"
        )

    async def test_endpoint_discovery_failure_raises_after_retry(
        self,
        cookidoo: Cookidoo,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A discovery failure that persists through the retry propagates."""

        async def _raise(*_args: object, **_kwargs: object) -> dict[str, str]:
            raise CookidooParseException("boom")

        monkeypatch.setattr(
            "cookidoo_api.cookidoo.resolve_endpoint_paths",
            _raise,
        )

        with pytest.raises(CookidooParseException):
            await cookidoo.get_user_info()

        assert not cookidoo._endpoints_resolved

    async def test_endpoint_discovery_runs_only_once_per_instance(
        self,
        mocked: aioresponses,
        cookidoo: Cookidoo,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Once resolved, discovery is not repeated on subsequent calls."""
        calls = 0

        async def _resolve(*_args: object, **_kwargs: object) -> dict[str, str]:
            nonlocal calls
            calls += 1
            return {
                "community-profile:user-private-profile": "community/profile/{language}",
                "ownership:subscriptions": "ownership/subscriptions",
            }

        monkeypatch.setattr(
            "cookidoo_api.cookidoo.resolve_endpoint_paths",
            _resolve,
        )
        mocked.get(
            "https://cookidoo.ch/community/profile/de-CH",
            payload=COOKIDOO_TEST_RESPONSE_USER_INFO,
            status=HTTPStatus.OK,
            repeat=True,
        )

        await cookidoo.get_user_info()
        await cookidoo.get_user_info()

        assert calls == 1

    async def test_endpoint_discovery_is_concurrency_safe(
        self,
        mocked: aioresponses,
        cookidoo: Cookidoo,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Concurrent callers on a fresh instance share a single discovery run."""
        calls = 0

        async def _resolve(*_args: object, **_kwargs: object) -> dict[str, str]:
            nonlocal calls
            calls += 1
            await asyncio.sleep(0)  # yield, so concurrent callers can interleave
            return {
                "community-profile:user-private-profile": "community/profile/{language}",
                "ownership:subscriptions": "ownership/subscriptions",
            }

        monkeypatch.setattr(
            "cookidoo_api.cookidoo.resolve_endpoint_paths",
            _resolve,
        )
        mocked.get(
            "https://cookidoo.ch/community/profile/de-CH",
            payload=COOKIDOO_TEST_RESPONSE_USER_INFO,
            status=HTTPStatus.OK,
            repeat=True,
        )

        await asyncio.gather(
            cookidoo.get_user_info(),
            cookidoo.get_user_info(),
            cookidoo.get_user_info(),
        )

        assert calls == 1

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.get(
            "https://cookidoo.ch/community/profile/de-CH",
            status=HTTPStatus.UNAUTHORIZED,
            payload={"error_description": ""},
        )
        with pytest.raises(CookidooAuthException):
            await cookidoo.get_user_info()

    async def test_non_mapping_response(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test response shape validation."""
        mocked.get(
            "https://cookidoo.ch/community/profile/de-CH",
            status=HTTPStatus.OK,
            payload=[],
        )

        with pytest.raises(CookidooParseException):
            await cookidoo.get_user_info()

    async def test_invalid_mapping_response(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test converter parse exception for missing keys."""
        mocked.get(
            "https://cookidoo.ch/community/profile/de-CH",
            status=HTTPStatus.OK,
            payload={},
        )

        with pytest.raises(CookidooParseException):
            await cookidoo.get_user_info()

    @pytest.mark.parametrize(
        ("status", "exception"),
        [
            (HTTPStatus.OK, CookidooParseException),
            (HTTPStatus.UNAUTHORIZED, CookidooAuthException),
        ],
    )
    async def test_parse_exception(
        self,
        mocked: aioresponses,
        cookidoo: Cookidoo,
        status: HTTPStatus,
        exception: type[CookidooException],
    ) -> None:
        """Test parse exceptions."""
        mocked.get(
            "https://cookidoo.ch/community/profile/de-CH",
            status=status,
            body="not json",
            content_type="application/json",
        )

        with pytest.raises(exception):
            await cookidoo.get_user_info()


class TestGetActiveSubscription:
    """Tests for get_active_subscription method."""

    async def test_get_active_subscription(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for get_active_subscription."""

        mocked.get(
            "https://cookidoo.ch/ownership/subscriptions",
            payload=COOKIDOO_TEST_RESPONSE_ACTIVE_SUBSCRIPTION,
            status=HTTPStatus.OK,
        )

        data = await cookidoo.get_active_subscription()
        assert data
        assert data.active
        assert data.status == "RUNNING"

    async def test_get_inactive_subscription(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for get_active_subscription."""

        mocked.get(
            "https://cookidoo.ch/ownership/subscriptions",
            payload=COOKIDOO_TEST_RESPONSE_INACTIVE_SUBSCRIPTION,
            status=HTTPStatus.OK,
        )

        data = await cookidoo.get_active_subscription()
        assert data is None

    async def test_get_devices(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test for get_devices with a single appliance."""
        mocked.get(
            "https://cookidoo.ch/customer-devices/api/my-devices/versions",
            payload=COOKIDOO_TEST_RESPONSE_DEVICES,
            status=HTTPStatus.OK,
        )

        devices = await cookidoo.get_devices()
        assert len(devices) == 1
        assert devices[0].type == ThermomixMachineType.TM7

    async def test_get_devices_multiple(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for get_devices with several appliances."""
        mocked.get(
            "https://cookidoo.ch/customer-devices/api/my-devices/versions",
            payload=COOKIDOO_TEST_RESPONSE_DEVICES_MULTIPLE,
            status=HTTPStatus.OK,
        )

        devices = await cookidoo.get_devices()
        assert [d.type for d in devices] == [
            ThermomixMachineType.TM7,
            ThermomixMachineType.TM6,
        ]

    async def test_get_devices_empty(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for get_devices with no paired appliance."""
        mocked.get(
            "https://cookidoo.ch/customer-devices/api/my-devices/versions",
            payload=COOKIDOO_TEST_RESPONSE_DEVICES_EMPTY,
            status=HTTPStatus.OK,
        )

        assert await cookidoo.get_devices() == []

    async def test_get_devices_no_content(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """An account without a paired appliance gets a 204 with an empty body."""
        mocked.get(
            "https://cookidoo.ch/customer-devices/api/my-devices/versions",
            status=HTTPStatus.NO_CONTENT,
        )

        assert await cookidoo.get_devices() == []

    async def test_get_devices_unknown_type(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """An unrecognized machine type raises a parse exception."""
        mocked.get(
            "https://cookidoo.ch/customer-devices/api/my-devices/versions",
            payload=["TM99"],
            status=HTTPStatus.OK,
        )

        with pytest.raises(CookidooParseException):
            await cookidoo.get_devices()

    async def test_non_sequence_response(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test response shape validation."""
        mocked.get(
            "https://cookidoo.ch/ownership/subscriptions",
            payload={},
            status=HTTPStatus.OK,
        )

        with pytest.raises(CookidooParseException):
            await cookidoo.get_active_subscription()

    async def test_subscription_missing_active(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test malformed subscription items."""
        mocked.get(
            "https://cookidoo.ch/ownership/subscriptions",
            payload=[{"status": "RUNNING"}],
            status=HTTPStatus.OK,
        )

        with pytest.raises(CookidooParseException):
            await cookidoo.get_active_subscription()

    @pytest.mark.parametrize(
        "exception",
        [
            TimeoutError,
            ClientError,
        ],
    )
    async def test_request_exception(
        self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception
    ) -> None:
        """Test request exceptions."""

        mocked.get(
            "https://cookidoo.ch/ownership/subscriptions",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.get_active_subscription()

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.get(
            "https://cookidoo.ch/ownership/subscriptions",
            status=HTTPStatus.UNAUTHORIZED,
            payload={"error_description": ""},
        )
        with pytest.raises(CookidooAuthException):
            await cookidoo.get_active_subscription()

    @pytest.mark.parametrize(
        ("status", "exception"),
        [
            (HTTPStatus.OK, CookidooParseException),
            (HTTPStatus.UNAUTHORIZED, CookidooAuthException),
        ],
    )
    async def test_parse_exception(
        self,
        mocked: aioresponses,
        cookidoo: Cookidoo,
        status: HTTPStatus,
        exception: type[CookidooException],
    ) -> None:
        """Test parse exceptions."""
        mocked.get(
            "https://cookidoo.ch/ownership/subscriptions",
            status=status,
            body="not json",
            content_type="application/json",
        )

        with pytest.raises(exception):
            await cookidoo.get_active_subscription()


class TestGetRecipeDetails:
    """Tests for get_recipe_details method."""

    async def test_get_recipe_details(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for get_recipe_details."""

        mocked.get(
            "https://cookidoo.ch/recipes/recipe/de-CH/r907015",
            payload=COOKIDOO_TEST_RESPONSE_GET_RECIPE_DETAILS,
            status=HTTPStatus.OK,
        )

        data = await cookidoo.get_recipe_details("r907015")
        assert data
        assert isinstance(data, object)
        assert data.id == "r907015"
        assert data.name == "Kokos Pralinen"
        assert isinstance(data.categories, list)
        assert isinstance(data.collections, list)
        assert isinstance(data.ingredients, list)
        assert isinstance(data.notes, list)
        assert isinstance(data.utensils, list)
        assert isinstance(data.active_time, int)
        assert isinstance(data.total_time, int)
        assert isinstance(data.serving_size, int)
        assert len(data.step_groups) == 1
        assert data.step_groups[0].title == ""
        assert len(data.step_groups[0].recipe_steps) == 4
        assert data.step_groups[0].recipe_steps[0].title == "1"
        assert (
            data.step_groups[0]
            .recipe_steps[0]
            .formatted_text.startswith("<NOBR>200 g Kokosraspeln</NOBR>")
        )

    @pytest.mark.parametrize(
        "exception",
        [
            TimeoutError,
            ClientError,
        ],
    )
    async def test_request_exception(
        self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception
    ) -> None:
        """Test request exceptions."""

        mocked.get(
            "https://cookidoo.ch/recipes/recipe/de-CH/r907015",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.get_recipe_details("r907015")

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.get(
            "https://cookidoo.ch/recipes/recipe/de-CH/r907015",
            status=HTTPStatus.UNAUTHORIZED,
            payload={"error_description": ""},
        )
        with pytest.raises(CookidooAuthException):
            await cookidoo.get_recipe_details("r907015")

    @pytest.mark.parametrize(
        ("status", "exception"),
        [
            (HTTPStatus.OK, CookidooParseException),
            (HTTPStatus.UNAUTHORIZED, CookidooAuthException),
        ],
    )
    async def test_parse_exception(
        self,
        mocked: aioresponses,
        cookidoo: Cookidoo,
        status: HTTPStatus,
        exception: type[CookidooException],
    ) -> None:
        """Test parse exceptions."""
        mocked.get(
            "https://cookidoo.ch/recipes/recipe/de-CH/r907015",
            status=status,
            body="not json",
            content_type="application/json",
        )

        with pytest.raises(exception):
            await cookidoo.get_recipe_details("r907015")

    async def test_missing_times_raises_parse_exception(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """A recipe missing a non-null activeTime/totalTime raises CookidooParseException.

        Previously this raised a bare StopIteration, which is not a documented
        exception of this method and is not even guaranteed to propagate as
        StopIteration out of an async function (PEP 479).
        """
        payload = COOKIDOO_TEST_RESPONSE_GET_RECIPE_DETAILS.copy()
        payload["times"] = []
        mocked.get(
            "https://cookidoo.ch/recipes/recipe/de-CH/r907015",
            payload=payload,
            status=HTTPStatus.OK,
        )

        with pytest.raises(CookidooParseException):
            await cookidoo.get_recipe_details("r907015")


class TestSearchRecipes:
    """Tests for search_recipes method."""

    async def test_search_recipes(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for search_recipes."""
        mocked.get(
            "https://cookidoo.ch/search/de?query=chicken",
            payload=COOKIDOO_TEST_RESPONSE_SEARCH_RECIPES,
            status=HTTPStatus.OK,
        )

        data = await cookidoo.search_recipes("chicken")
        assert isinstance(data, CookidooSearchResult)
        assert data.total == 2
        assert len(data.recipes) == 2
        assert data.recipes[0].id == "r123456"
        assert data.recipes[0].name == "Chicken Soup"
        assert data.recipes[0].thumbnail == (
            "https://assets.tmecosys.com/image/upload/"
            "t_web_shared_recipe_221x240/img/recipe/ras/Assets/"
            "a1b2c3d4-1111-2222-3333-444455556666/Derivates/"
            "abcdef01-2345-6789-abcd-ef0123456789.jpg"
        )
        assert data.recipes[0].image == (
            "https://assets.tmecosys.com/image/upload/"
            "t_web_rdp_recipe_584x480_1_5x/img/recipe/ras/Assets/"
            "a1b2c3d4-1111-2222-3333-444455556666/Derivates/"
            "abcdef01-2345-6789-abcd-ef0123456789.jpg"
        )
        assert data.recipes[0].url == (
            "https://cookidoo.ch/recipes/recipe/de-CH/r123456"
        )
        assert data.recipes[1].id == "r654321"
        assert data.recipes[1].name == "Chicken Salad"
        assert data.recipes[1].thumbnail == (
            "https://assets.tmecosys.com/image/upload/"
            "t_web_shared_recipe_221x240/img/recipe/ras/Assets/"
            "f1e2d3c4-9999-8888-7777-666655554444/Derivates/"
            "98765432-10fe-dcba-9876-543210fedcba.jpg"
        )
        assert data.recipes[1].image == (
            "https://assets.tmecosys.com/image/upload/"
            "t_web_rdp_recipe_584x480_1_5x/img/recipe/ras/Assets/"
            "f1e2d3c4-9999-8888-7777-666655554444/Derivates/"
            "98765432-10fe-dcba-9876-543210fedcba.jpg"
        )
        assert data.recipes[1].url == (
            "https://cookidoo.ch/recipes/recipe/de-CH/r654321"
        )

    async def test_search_recipes_with_options(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test search_recipes with filters and list parameters."""
        accessories = [
            "includingFriend",
            "includingBladeCover",
            "includingBladeCoverWithPeeler",
            "includingCutter",
            "includingSensor",
        ]
        categories = [
            "VrkNavCategory-RPF-001",
            "VrkNavCategory-RPF-002",
            "VrkNavCategory-RPF-003",
        ]
        url = (
            "https://cookidoo.ch/search/es?"
            "query=chicken"
            "&accessories=includingFriend,includingBladeCover,includingBladeCoverWithPeeler,includingCutter,includingSensor"
            "&languages=en,es"
            "&categories=VrkNavCategory-RPF-001,VrkNavCategory-RPF-002,VrkNavCategory-RPF-003"
            "&countries=ar,es"
            "&ingredients=sal,aceite%20de%20oliva"
            "&excludeIngredients=polvo%20de%20hornear"
            "&tags=De%20diario"
            "&ratings=5,4"
            "&difficulty=easy"
            "&preparationTime=900"
            "&totalTime=1200"
            "&portions=2"
            "&page=1"
            "&pageSize=10"
            "&tmv=TM7,TM6,TM5,TM31"
        )
        mocked.get(
            url,
            payload=COOKIDOO_TEST_RESPONSE_SEARCH_RECIPES,
            status=HTTPStatus.OK,
        )

        data = await cookidoo.search_recipes(
            "chicken",
            locale="es",
            accessories=accessories,
            languages=["en", "es"],
            categories=categories,
            countries=["ar", "es"],
            ingredients=["sal", "aceite de oliva"],
            exclude_ingredients=["polvo de hornear"],
            tags=["De diario"],
            ratings=["5", "4"],
            difficulty="easy",
            preparation_time=900,
            total_time=1200,
            portions=2,
            page=1,
            page_size=10,
            tmv=["TM7", "TM6", "TM5", "TM31"],
        )
        assert isinstance(data, CookidooSearchResult)
        assert len(data.recipes) == 2
        assert data.total == 2

    @pytest.mark.parametrize(
        "exception",
        [
            TimeoutError,
            ClientError,
        ],
    )
    async def test_search_recipes_request_exception(
        self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception
    ) -> None:
        """Test search_recipes request exceptions."""
        mocked.get(
            "https://cookidoo.ch/search/de?query=chicken",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.search_recipes("chicken")

    async def test_search_recipes_unauthorized(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test search_recipes unauthorized exception."""
        mocked.get(
            "https://cookidoo.ch/search/de?query=chicken",
            status=HTTPStatus.UNAUTHORIZED,
            payload={"error_description": ""},
        )
        with pytest.raises(CookidooAuthException):
            await cookidoo.search_recipes("chicken")

    async def test_search_recipes_unauthorized_non_json_body(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test search_recipes 401 with non-JSON body still raises CookidooAuthException."""
        mocked.get(
            "https://cookidoo.ch/search/de?query=chicken",
            status=HTTPStatus.UNAUTHORIZED,
            body="not json",
            content_type="text/plain",
        )
        with pytest.raises(CookidooAuthException):
            await cookidoo.search_recipes("chicken")

    async def test_search_recipes_parse_exception(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test search_recipes raises CookidooParseException when response is not valid JSON."""
        mocked.get(
            "https://cookidoo.ch/search/de?query=chicken",
            status=HTTPStatus.OK,
            body="not valid json",
            content_type="application/json",
        )
        with pytest.raises(CookidooParseException):
            await cookidoo.search_recipes("chicken")

    async def test_search_recipes_no_content(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test search_recipes when API returns 204 No Content."""
        mocked.get(
            "https://cookidoo.ch/search/de?query=chicken",
            status=HTTPStatus.NO_CONTENT,
        )

        data = await cookidoo.search_recipes("chicken")
        assert isinstance(data, CookidooSearchResult)
        assert data.recipes == []
        assert data.total == 0

    async def test_search_recipes_with_string_params(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test search_recipes with string (non-list) filter params."""
        url = (
            "https://cookidoo.ch/search/de?"
            "query=pasta&accessories=includingFriend&difficulty=easy"
        )
        mocked.get(
            url,
            payload=COOKIDOO_TEST_RESPONSE_SEARCH_RECIPES,
            status=HTTPStatus.OK,
        )

        data = await cookidoo.search_recipes(
            "pasta",
            accessories="includingFriend",
            difficulty="easy",
        )
        assert isinstance(data, CookidooSearchResult)
        assert data.total == 2

    async def test_search_recipes_with_tmv_single_enum(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test search_recipes with single ThermomixMachineType (not list)."""
        url = "https://cookidoo.ch/search/de?query=soup&tmv=TM7"
        mocked.get(
            url,
            payload=COOKIDOO_TEST_RESPONSE_SEARCH_RECIPES,
            status=HTTPStatus.OK,
        )

        data = await cookidoo.search_recipes("soup", tmv=ThermomixMachineType.TM7)
        assert isinstance(data, CookidooSearchResult)
        assert data.total == 2

    async def test_search_recipes_without_query(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test search_recipes with optional query omitted (params without query)."""
        mocked.get(
            "https://cookidoo.ch/search/de",
            payload=COOKIDOO_TEST_RESPONSE_SEARCH_RECIPES,
            status=HTTPStatus.OK,
        )

        data = await cookidoo.search_recipes()
        assert isinstance(data, CookidooSearchResult)
        assert len(data.recipes) == 2
        assert data.total == 2

    async def test_search_recipes_unexpected_status(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test search_recipes raises CookidooRequestException on unexpected status."""
        mocked.get(
            "https://cookidoo.ch/search/de?query=chicken",
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
        )
        with pytest.raises(CookidooRequestException):
            await cookidoo.search_recipes("chicken")

    async def test_search_recipes_non_dict_response(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test search_recipes raises CookidooParseException when response is not a dict."""
        mocked.get(
            "https://cookidoo.ch/search/de?query=chicken",
            payload=["not", "a", "dict"],
            status=HTTPStatus.OK,
        )
        with pytest.raises(CookidooParseException):
            await cookidoo.search_recipes("chicken")


class TestGetCustomRecipe:
    """Tests for get_custom_recipe method."""

    async def test_get_custom_recipe(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for get_custom_recipe."""

        mocked.get(
            "https://cookidoo.ch/created-recipes/de-CH/01K2CVHD1DXG1PVETNVV3JPKWW",
            payload=COOKIDOO_TEST_RESPONSE_GET_CUSTOM_RECIPE,
            status=HTTPStatus.OK,
        )

        data = await cookidoo.get_custom_recipe("01K2CVHD1DXG1PVETNVV3JPKWW")
        assert data
        assert isinstance(data, object)
        assert data.id == "01K2CVHD1DXG1PVETNVV3JPKWW"
        assert data.name == "Vongole alla marinara"
        assert isinstance(data.instructions, list)
        assert isinstance(data.ingredients, list)
        assert isinstance(data.tools, list)
        assert isinstance(data.active_time, int)
        assert isinstance(data.total_time, int)
        assert isinstance(data.serving_size, int)

    @pytest.mark.parametrize(
        "exception",
        [
            TimeoutError,
            ClientError,
        ],
    )
    async def test_request_exception(
        self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception
    ) -> None:
        """Test request exceptions."""

        mocked.get(
            "https://cookidoo.ch/created-recipes/de-CH/01K2CVHD1DXG1PVETNVV3JPKWW",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.get_custom_recipe("01K2CVHD1DXG1PVETNVV3JPKWW")

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.get(
            "https://cookidoo.ch/created-recipes/de-CH/01K2CVHD1DXG1PVETNVV3JPKWW",
            status=HTTPStatus.UNAUTHORIZED,
            payload={"error_description": ""},
        )
        with pytest.raises(CookidooAuthException):
            await cookidoo.get_custom_recipe("01K2CVHD1DXG1PVETNVV3JPKWW")

    @pytest.mark.parametrize(
        ("status", "exception"),
        [
            (HTTPStatus.OK, CookidooParseException),
            (HTTPStatus.UNAUTHORIZED, CookidooAuthException),
        ],
    )
    async def test_parse_exception(
        self,
        mocked: aioresponses,
        cookidoo: Cookidoo,
        status: HTTPStatus,
        exception: type[CookidooException],
    ) -> None:
        """Test parse exceptions."""
        mocked.get(
            "https://cookidoo.ch/created-recipes/de-CH/01K2CVHD1DXG1PVETNVV3JPKWW",
            status=status,
            body="not json",
            content_type="application/json",
        )

        with pytest.raises(exception):
            await cookidoo.get_custom_recipe("01K2CVHD1DXG1PVETNVV3JPKWW")


class TestListCustomRecipes:
    """Tests for list_custom_recipes method."""

    async def test_list_custom_recipes(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for list_custom_recipes."""
        mocked.get(
            "https://cookidoo.ch/created-recipes/de-CH",
            payload=COOKIDOO_TEST_RESPONSE_LIST_CUSTOM_RECIPES,
            status=HTTPStatus.OK,
        )

        data = await cookidoo.list_custom_recipes()

        assert len(data) == 1
        assert data[0].id == "01K2CTJ9Y1BABRG5MXK44CFZS4"
        assert data[0].name == "Vongole alla marinara"
        assert data[0].active_time == 600
        assert data[0].total_time == 1800
        assert data[0].ingredients == [
            "130 g di cipolla",
            "65 g di olio extravergine di oliva",
        ]

    async def test_list_custom_recipes_empty(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for list_custom_recipes with no recipes."""
        mocked.get(
            "https://cookidoo.ch/created-recipes/de-CH",
            payload={"items": []},
            status=HTTPStatus.OK,
        )

        data = await cookidoo.list_custom_recipes()

        assert data == []

    @pytest.mark.parametrize(
        "exception",
        [
            TimeoutError,
            ClientError,
        ],
    )
    async def test_request_exception(
        self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception
    ) -> None:
        """Test request exceptions."""
        mocked.get(
            "https://cookidoo.ch/created-recipes/de-CH",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.list_custom_recipes()

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.get(
            "https://cookidoo.ch/created-recipes/de-CH",
            status=HTTPStatus.UNAUTHORIZED,
            payload={"error_description": ""},
        )

        with pytest.raises(CookidooAuthException):
            await cookidoo.list_custom_recipes()

    @pytest.mark.parametrize(
        ("payload", "exception"),
        [
            ({}, CookidooParseException),
            ({"items": None}, CookidooParseException),
        ],
    )
    async def test_parse_exception(
        self,
        mocked: aioresponses,
        cookidoo: Cookidoo,
        payload: dict[str, object],
        exception: type[CookidooException],
    ) -> None:
        """Test parse exceptions."""
        mocked.get(
            "https://cookidoo.ch/created-recipes/de-CH",
            status=HTTPStatus.OK,
            payload=payload,
        )

        with pytest.raises(exception):
            await cookidoo.list_custom_recipes()


class TestAddCustomRecipe:
    """Tests for add_custom_recipe method."""

    async def test_add_custom_recipe(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for add_custom_recipe."""

        mocked.post(
            "https://cookidoo.ch/created-recipes/de-CH",
            payload=COOKIDOO_TEST_RESPONSE_ADD_CUSTOM_RECIPE,
            status=HTTPStatus.OK,
        )

        data = await cookidoo.add_custom_recipe_from("r907015", 4)
        assert data
        assert data.id == "01K2CTJ9Y1BABRG5MXK44CFZS4"
        assert data.name == "Vongole alla marinara"

    @pytest.mark.parametrize(
        "exception",
        [
            TimeoutError,
            ClientError,
        ],
    )
    async def test_request_exception(
        self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception
    ) -> None:
        """Test request exceptions."""

        mocked.post(
            "https://cookidoo.ch/created-recipes/de-CH",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.add_custom_recipe_from("r907015", 4)

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.post(
            "https://cookidoo.ch/created-recipes/de-CH",
            status=HTTPStatus.UNAUTHORIZED,
            payload={"error_description": ""},
        )
        with pytest.raises(CookidooAuthException):
            await cookidoo.add_custom_recipe_from("r907015", 4)

    @pytest.mark.parametrize(
        ("status", "exception"),
        [
            (HTTPStatus.OK, CookidooParseException),
            (HTTPStatus.UNAUTHORIZED, CookidooAuthException),
        ],
    )
    async def test_parse_exception(
        self,
        mocked: aioresponses,
        cookidoo: Cookidoo,
        status: HTTPStatus,
        exception: type[CookidooException],
    ) -> None:
        """Test parse exceptions."""
        mocked.post(
            "https://cookidoo.ch/created-recipes/de-CH",
            status=status,
            body="not json",
            content_type="application/json",
        )

        with pytest.raises(exception):
            await cookidoo.add_custom_recipe_from("r907015", 4)


class TestRemoveCustomRecipe:
    """Tests for remove_custom_recipe method."""

    async def test_remove_custom_recipe(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for remove_custom_recipe."""

        mocked.delete(
            "https://cookidoo.ch/created-recipes/de-CH/01K2CTJ9Y1BABRG5MXK44CFZS4",
            payload=None,
            status=HTTPStatus.OK,
        )

        await cookidoo.remove_custom_recipe("01K2CTJ9Y1BABRG5MXK44CFZS4")

    @pytest.mark.parametrize(
        "exception",
        [
            TimeoutError,
            ClientError,
        ],
    )
    async def test_request_exception(
        self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception
    ) -> None:
        """Test request exceptions."""

        mocked.delete(
            "https://cookidoo.ch/created-recipes/de-CH/01K2CTJ9Y1BABRG5MXK44CFZS4",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.remove_custom_recipe("01K2CTJ9Y1BABRG5MXK44CFZS4")

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.delete(
            "https://cookidoo.ch/created-recipes/de-CH/01K2CTJ9Y1BABRG5MXK44CFZS4",
            status=HTTPStatus.UNAUTHORIZED,
            payload={"error_description": ""},
        )
        with pytest.raises(CookidooAuthException):
            await cookidoo.remove_custom_recipe("01K2CTJ9Y1BABRG5MXK44CFZS4")

    @pytest.mark.parametrize(
        ("status", "exception"),
        [
            # (HTTPStatus.OK, CookidooParseException), # There is nothing to parse
            (HTTPStatus.UNAUTHORIZED, CookidooAuthException),
        ],
    )
    async def test_parse_exception(
        self,
        mocked: aioresponses,
        cookidoo: Cookidoo,
        status: HTTPStatus,
        exception: type[CookidooException],
    ) -> None:
        """Test parse exceptions."""
        mocked.delete(
            "https://cookidoo.ch/created-recipes/de-CH/01K2CTJ9Y1BABRG5MXK44CFZS4",
            status=status,
            body="not json",
            content_type="application/json",
        )

        with pytest.raises(exception):
            await cookidoo.remove_custom_recipe("01K2CTJ9Y1BABRG5MXK44CFZS4")


class TestGetShoppingListRecipes:
    """Tests for get_shopping_list_recipes method."""

    async def test_get_shopping_list_recipes(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for get_shopping_list_recipes."""

        mocked.get(
            "https://cookidoo.ch/shopping/de-CH",
            payload=COOKIDOO_TEST_RESPONSE_GET_SHOPPING_LIST_RECIPES,
            status=HTTPStatus.OK,
        )

        data = await cookidoo.get_shopping_list_recipes()
        assert data
        assert isinstance(data, list)
        assert len(data) == 2

    @pytest.mark.parametrize(
        "exception",
        [
            TimeoutError,
            ClientError,
        ],
    )
    async def test_request_exception(
        self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception
    ) -> None:
        """Test request exceptions."""

        mocked.get(
            "https://cookidoo.ch/shopping/de-CH",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.get_shopping_list_recipes()

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.get(
            "https://cookidoo.ch/shopping/de-CH",
            status=HTTPStatus.UNAUTHORIZED,
            payload={"error_description": ""},
        )
        with pytest.raises(CookidooAuthException):
            await cookidoo.get_shopping_list_recipes()

    @pytest.mark.parametrize(
        ("status", "exception"),
        [
            (HTTPStatus.OK, CookidooParseException),
            (HTTPStatus.UNAUTHORIZED, CookidooAuthException),
        ],
    )
    async def test_parse_exception(
        self,
        mocked: aioresponses,
        cookidoo: Cookidoo,
        status: HTTPStatus,
        exception: type[CookidooException],
    ) -> None:
        """Test parse exceptions."""
        mocked.get(
            "https://cookidoo.ch/shopping/de-CH",
            status=status,
            body="not json",
            content_type="application/json",
        )

        with pytest.raises(exception):
            await cookidoo.get_shopping_list_recipes()


class TestGetIngredients:
    """Tests for get_ingredient_items method."""

    async def test_get_ingredient_items_for_recipes(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for get_ingredient_items."""

        mocked.get(
            "https://cookidoo.ch/shopping/de-CH",
            payload=COOKIDOO_TEST_RESPONSE_GET_INGREDIENTS_FOR_RECIPES,
            status=HTTPStatus.OK,
        )

        data = await cookidoo.get_ingredient_items()
        assert data
        assert isinstance(data, list)
        assert len(data) == 14

    async def test_get_ingredient_items_for_custom_recipes(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for get_ingredient_items."""

        mocked.get(
            "https://cookidoo.ch/shopping/de-CH",
            payload=COOKIDOO_TEST_RESPONSE_GET_INGREDIENTS_FOR_CUSTOM_RECIPES,
            status=HTTPStatus.OK,
        )

        data = await cookidoo.get_ingredient_items()
        assert data
        assert isinstance(data, list)
        assert len(data) == 10

    @pytest.mark.parametrize(
        "exception",
        [
            TimeoutError,
            ClientError,
        ],
    )
    async def test_request_exception(
        self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception
    ) -> None:
        """Test request exceptions."""

        mocked.get(
            "https://cookidoo.ch/shopping/de-CH",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.get_ingredient_items()

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.get(
            "https://cookidoo.ch/shopping/de-CH",
            status=HTTPStatus.UNAUTHORIZED,
            payload={"error_description": ""},
        )
        with pytest.raises(CookidooAuthException):
            await cookidoo.get_ingredient_items()

    @pytest.mark.parametrize(
        ("status", "exception"),
        [
            (HTTPStatus.OK, CookidooParseException),
            (HTTPStatus.UNAUTHORIZED, CookidooAuthException),
        ],
    )
    async def test_parse_exception(
        self,
        mocked: aioresponses,
        cookidoo: Cookidoo,
        status: HTTPStatus,
        exception: type[CookidooException],
    ) -> None:
        """Test parse exceptions."""
        mocked.get(
            "https://cookidoo.ch/shopping/de-CH",
            status=status,
            body="not json",
            content_type="application/json",
        )

        with pytest.raises(exception):
            await cookidoo.get_ingredient_items()


class TestAddIngredientsForRecipes:
    """Tests for add_ingredient_items_for_recipes method."""

    async def test_add_ingredient_items_for_recipes(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for add_ingredient_items_for_recipes."""

        mocked.post(
            "https://cookidoo.ch/shopping/de-CH/recipes/add",
            payload=COOKIDOO_TEST_RESPONSE_ADD_INGREDIENTS_FOR_RECIPES,
            status=HTTPStatus.OK,
        )

        data = await cookidoo.add_ingredient_items_for_recipes(["r59322", "r907016"])
        assert data
        assert isinstance(data, list)
        assert len(data) == 14

    @pytest.mark.parametrize(
        "exception",
        [
            TimeoutError,
            ClientError,
        ],
    )
    async def test_request_exception(
        self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception
    ) -> None:
        """Test request exceptions."""

        mocked.post(
            "https://cookidoo.ch/shopping/de-CH/recipes/add",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.add_ingredient_items_for_recipes(["r59322", "r907016"])

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.post(
            "https://cookidoo.ch/shopping/de-CH/recipes/add",
            status=HTTPStatus.UNAUTHORIZED,
            payload={"error_description": ""},
        )
        with pytest.raises(CookidooAuthException):
            await cookidoo.add_ingredient_items_for_recipes(["r59322", "r907016"])

    @pytest.mark.parametrize(
        ("status", "exception"),
        [
            (HTTPStatus.OK, CookidooParseException),
            (HTTPStatus.UNAUTHORIZED, CookidooAuthException),
        ],
    )
    async def test_parse_exception(
        self,
        mocked: aioresponses,
        cookidoo: Cookidoo,
        status: HTTPStatus,
        exception: type[CookidooException],
    ) -> None:
        """Test parse exceptions."""
        mocked.post(
            "https://cookidoo.ch/shopping/de-CH/recipes/add",
            status=status,
            body="not json",
            content_type="application/json",
        )

        with pytest.raises(exception):
            await cookidoo.add_ingredient_items_for_recipes(["r59322", "r907016"])


class TestRemoveIngredientsForRecipes:
    """Tests for remove_ingredient_items_for_recipes method."""

    async def test_remove_ingredient_items_for_recipes(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for remove_ingredient_items_for_recipes."""

        mocked.post(
            "https://cookidoo.ch/shopping/de-CH/recipes/remove",
            payload=None,
            status=HTTPStatus.OK,
        )

        await cookidoo.remove_ingredient_items_for_recipes(["r59322", "r907016"])

    @pytest.mark.parametrize(
        "exception",
        [
            TimeoutError,
            ClientError,
        ],
    )
    async def test_request_exception(
        self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception
    ) -> None:
        """Test request exceptions."""

        mocked.post(
            "https://cookidoo.ch/shopping/de-CH/recipes/remove",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.remove_ingredient_items_for_recipes(["r59322", "r907016"])

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.post(
            "https://cookidoo.ch/shopping/de-CH/recipes/remove",
            status=HTTPStatus.UNAUTHORIZED,
            payload={"error_description": ""},
        )
        with pytest.raises(CookidooAuthException):
            await cookidoo.remove_ingredient_items_for_recipes(["r59322", "r907016"])

    @pytest.mark.parametrize(
        ("status", "exception"),
        [
            # (HTTPStatus.OK, CookidooParseException), # There is nothing to parse
            (HTTPStatus.UNAUTHORIZED, CookidooAuthException),
        ],
    )
    async def test_parse_exception(
        self,
        mocked: aioresponses,
        cookidoo: Cookidoo,
        status: HTTPStatus,
        exception: type[CookidooException],
    ) -> None:
        """Test parse exceptions."""
        mocked.post(
            "https://cookidoo.ch/shopping/de-CH/recipes/remove",
            status=status,
            body="not json",
            content_type="application/json",
        )

        with pytest.raises(exception):
            await cookidoo.remove_ingredient_items_for_recipes(["r59322", "r907016"])


class TestEditIngredientsOwnership:
    """Tests for edit_ingredient_items_ownership method."""

    async def test_edit_ingredient_items_ownership(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for edit_ingredient_items_ownership."""

        mocked.post(
            "https://cookidoo.ch/shopping/de-CH/owned-ingredients/ownership/edit",
            payload=COOKIDOO_TEST_RESPONSE_EDIT_INGREDIENTS_OWNERSHIP,
            status=HTTPStatus.OK,
        )

        data = await cookidoo.edit_ingredient_items_ownership(
            [
                CookidooIngredientItem(
                    id="01JBQG02JQD3XPFMM5CXE51K25",
                    name="Hefe",
                    is_owned=True,
                    description="1 Würfel",
                )
            ]
        )
        assert data
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0].is_owned

    @pytest.mark.parametrize(
        "exception",
        [
            TimeoutError,
            ClientError,
        ],
    )
    async def test_request_exception(
        self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception
    ) -> None:
        """Test request exceptions."""

        mocked.post(
            "https://cookidoo.ch/shopping/de-CH/owned-ingredients/ownership/edit",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.edit_ingredient_items_ownership(
                [
                    CookidooIngredientItem(
                        id="01JBQG02JQD3XPFMM5CXE51K25",
                        name="Hefe",
                        is_owned=True,
                        description="1 Würfel",
                    )
                ]
            )

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.post(
            "https://cookidoo.ch/shopping/de-CH/owned-ingredients/ownership/edit",
            status=HTTPStatus.UNAUTHORIZED,
            payload={"error_description": ""},
        )
        with pytest.raises(CookidooAuthException):
            await cookidoo.edit_ingredient_items_ownership(
                [
                    CookidooIngredientItem(
                        id="01JBQG02JQD3XPFMM5CXE51K25",
                        name="Hefe",
                        is_owned=True,
                        description="1 Würfel",
                    )
                ]
            )

    @pytest.mark.parametrize(
        ("status", "exception"),
        [
            (HTTPStatus.OK, CookidooParseException),
            (HTTPStatus.UNAUTHORIZED, CookidooAuthException),
        ],
    )
    async def test_parse_exception(
        self,
        mocked: aioresponses,
        cookidoo: Cookidoo,
        status: HTTPStatus,
        exception: type[CookidooException],
    ) -> None:
        """Test parse exceptions."""
        mocked.post(
            "https://cookidoo.ch/shopping/de-CH/owned-ingredients/ownership/edit",
            status=status,
            body="not json",
            content_type="application/json",
        )

        with pytest.raises(exception):
            await cookidoo.edit_ingredient_items_ownership(
                [
                    CookidooIngredientItem(
                        id="01JBQG02JQD3XPFMM5CXE51K25",
                        name="Hefe",
                        is_owned=True,
                        description="1 Würfel",
                    )
                ]
            )


class TestAddIngredientsForCustomRecipes:
    """Tests for add_ingredient_items_for_custom_recipes method."""

    async def test_add_ingredient_items_for_custom_recipes(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for add_ingredient_items_for_custom_recipes."""

        mocked.post(
            "https://cookidoo.ch/shopping/de-CH/recipes/add",
            payload=COOKIDOO_TEST_RESPONSE_ADD_INGREDIENTS_FOR_CUSTOM_RECIPES,
            status=HTTPStatus.OK,
        )

        data = await cookidoo.add_ingredient_items_for_custom_recipes(
            ["01K2CTZSSKFKJWPM71017SJYMC"]
        )
        assert data
        assert isinstance(data, list)
        assert len(data) == 10

    @pytest.mark.parametrize(
        "exception",
        [
            TimeoutError,
            ClientError,
        ],
    )
    async def test_request_exception(
        self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception
    ) -> None:
        """Test request exceptions."""

        mocked.post(
            "https://cookidoo.ch/shopping/de-CH/recipes/add",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.add_ingredient_items_for_custom_recipes(
                ["01K2CTZSSKFKJWPM71017SJYMC"]
            )

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.post(
            "https://cookidoo.ch/shopping/de-CH/recipes/add",
            status=HTTPStatus.UNAUTHORIZED,
            payload={"error_description": ""},
        )
        with pytest.raises(CookidooAuthException):
            await cookidoo.add_ingredient_items_for_custom_recipes(
                ["01K2CTZSSKFKJWPM71017SJYMC"]
            )

    @pytest.mark.parametrize(
        ("status", "exception"),
        [
            (HTTPStatus.OK, CookidooParseException),
            (HTTPStatus.UNAUTHORIZED, CookidooAuthException),
        ],
    )
    async def test_parse_exception(
        self,
        mocked: aioresponses,
        cookidoo: Cookidoo,
        status: HTTPStatus,
        exception: type[CookidooException],
    ) -> None:
        """Test parse exceptions."""
        mocked.post(
            "https://cookidoo.ch/shopping/de-CH/recipes/add",
            status=status,
            body="not json",
            content_type="application/json",
        )

        with pytest.raises(exception):
            await cookidoo.add_ingredient_items_for_custom_recipes(
                ["01K2CTZSSKFKJWPM71017SJYMC"]
            )


class TestRemoveIngredientsForCustomRecipes:
    """Tests for remove_ingredient_items_for_custom_recipes method."""

    async def test_remove_ingredient_items_for_custom_recipes(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for remove_ingredient_items_for_custom_recipes."""

        mocked.post(
            "https://cookidoo.ch/shopping/de-CH/recipes/remove",
            payload=None,
            status=HTTPStatus.OK,
        )

        await cookidoo.remove_ingredient_items_for_custom_recipes(
            ["01K2CTZSSKFKJWPM71017SJYMC"]
        )

    @pytest.mark.parametrize(
        "exception",
        [
            TimeoutError,
            ClientError,
        ],
    )
    async def test_request_exception(
        self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception
    ) -> None:
        """Test request exceptions."""

        mocked.post(
            "https://cookidoo.ch/shopping/de-CH/recipes/remove",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.remove_ingredient_items_for_custom_recipes(
                ["01K2CTZSSKFKJWPM71017SJYMC"]
            )

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.post(
            "https://cookidoo.ch/shopping/de-CH/recipes/remove",
            status=HTTPStatus.UNAUTHORIZED,
            payload={"error_description": ""},
        )
        with pytest.raises(CookidooAuthException):
            await cookidoo.remove_ingredient_items_for_custom_recipes(
                ["01K2CTZSSKFKJWPM71017SJYMC"]
            )

    @pytest.mark.parametrize(
        ("status", "exception"),
        [
            # (HTTPStatus.OK, CookidooParseException), # There is nothing to parse
            (HTTPStatus.UNAUTHORIZED, CookidooAuthException),
        ],
    )
    async def test_parse_exception(
        self,
        mocked: aioresponses,
        cookidoo: Cookidoo,
        status: HTTPStatus,
        exception: type[CookidooException],
    ) -> None:
        """Test parse exceptions."""
        mocked.post(
            "https://cookidoo.ch/shopping/de-CH/recipes/remove",
            status=status,
            body="not json",
            content_type="application/json",
        )

        with pytest.raises(exception):
            await cookidoo.remove_ingredient_items_for_custom_recipes(
                ["01K2CTZSSKFKJWPM71017SJYMC"]
            )


class TestGetAdditionalItems:
    """Tests for get_additional_items method."""

    async def test_get_additional_items(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for get_additional_items."""

        mocked.get(
            "https://cookidoo.ch/shopping/de-CH",
            payload=COOKIDOO_TEST_RESPONSE_GET_ADDITIONAL_ITEMS,
            status=HTTPStatus.OK,
        )

        data = await cookidoo.get_additional_items()
        assert data
        assert isinstance(data, list)
        assert len(data) == 2

    @pytest.mark.parametrize(
        "exception",
        [
            TimeoutError,
            ClientError,
        ],
    )
    async def test_request_exception(
        self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception
    ) -> None:
        """Test request exceptions."""

        mocked.get(
            "https://cookidoo.ch/shopping/de-CH",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.get_additional_items()

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.get(
            "https://cookidoo.ch/shopping/de-CH",
            status=HTTPStatus.UNAUTHORIZED,
            payload={"error_description": ""},
        )
        with pytest.raises(CookidooAuthException):
            await cookidoo.get_additional_items()

    @pytest.mark.parametrize(
        ("status", "exception"),
        [
            (HTTPStatus.OK, CookidooParseException),
            (HTTPStatus.UNAUTHORIZED, CookidooAuthException),
        ],
    )
    async def test_parse_exception(
        self,
        mocked: aioresponses,
        cookidoo: Cookidoo,
        status: HTTPStatus,
        exception: type[CookidooException],
    ) -> None:
        """Test parse exceptions."""
        mocked.get(
            "https://cookidoo.ch/shopping/de-CH",
            status=status,
            body="not json",
            content_type="application/json",
        )

        with pytest.raises(exception):
            await cookidoo.get_additional_items()


class TestAddAdditionalItems:
    """Tests for add_additional_items method."""

    async def test_add_additional_items(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for add_additional_items."""

        mocked.post(
            "https://cookidoo.ch/shopping/de-CH/additional-items/add",
            payload=COOKIDOO_TEST_RESPONSE_ADD_ADDITIONAL_ITEMS,
            status=HTTPStatus.OK,
        )

        data = await cookidoo.add_additional_items(["Fleisch", "Fisch"])
        assert data
        assert isinstance(data, list)
        assert len(data) == 2

    @pytest.mark.parametrize(
        "exception",
        [
            TimeoutError,
            ClientError,
        ],
    )
    async def test_request_exception(
        self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception
    ) -> None:
        """Test request exceptions."""

        mocked.post(
            "https://cookidoo.ch/shopping/de-CH/additional-items/add",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.add_additional_items(["Fleisch", "Fisch"])

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.post(
            "https://cookidoo.ch/shopping/de-CH/additional-items/add",
            status=HTTPStatus.UNAUTHORIZED,
            payload={"error_description": ""},
        )
        with pytest.raises(CookidooAuthException):
            await cookidoo.add_additional_items(["Fleisch", "Fisch"])

    @pytest.mark.parametrize(
        ("status", "exception"),
        [
            (HTTPStatus.OK, CookidooParseException),
            (HTTPStatus.UNAUTHORIZED, CookidooAuthException),
        ],
    )
    async def test_parse_exception(
        self,
        mocked: aioresponses,
        cookidoo: Cookidoo,
        status: HTTPStatus,
        exception: type[CookidooException],
    ) -> None:
        """Test parse exceptions."""
        mocked.post(
            "https://cookidoo.ch/shopping/de-CH/additional-items/add",
            status=status,
            body="not json",
            content_type="application/json",
        )

        with pytest.raises(exception):
            await cookidoo.add_additional_items(["Fleisch", "Fisch"])


class TestRemoveAdditionalItems:
    """Tests for remove_ingredient_items_for_recipes method."""

    async def test_remove_ingredient_items_for_recipes(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for remove_ingredient_items_for_recipes."""

        mocked.post(
            "https://cookidoo.ch/shopping/de-CH/additional-items/remove",
            payload=None,
            status=HTTPStatus.OK,
        )

        await cookidoo.remove_additional_items(
            ["01JBQGDMRMR7RJW1C8AWDGD6YP", "01JBQGDMRNHAM7AMCR6YKPYKJQ"]
        )

    @pytest.mark.parametrize(
        "exception",
        [
            TimeoutError,
            ClientError,
        ],
    )
    async def test_request_exception(
        self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception
    ) -> None:
        """Test request exceptions."""

        mocked.post(
            "https://cookidoo.ch/shopping/de-CH/additional-items/remove",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.remove_additional_items(
                ["01JBQGDMRMR7RJW1C8AWDGD6YP", "01JBQGDMRNHAM7AMCR6YKPYKJQ"]
            )

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.post(
            "https://cookidoo.ch/shopping/de-CH/additional-items/remove",
            status=HTTPStatus.UNAUTHORIZED,
            payload={"error_description": ""},
        )
        with pytest.raises(CookidooAuthException):
            await cookidoo.remove_additional_items(
                ["01JBQGDMRMR7RJW1C8AWDGD6YP", "01JBQGDMRNHAM7AMCR6YKPYKJQ"]
            )

    @pytest.mark.parametrize(
        ("status", "exception"),
        [
            # (HTTPStatus.OK, CookidooParseException), # There is nothing to parse
            (HTTPStatus.UNAUTHORIZED, CookidooAuthException),
        ],
    )
    async def test_parse_exception(
        self,
        mocked: aioresponses,
        cookidoo: Cookidoo,
        status: HTTPStatus,
        exception: type[CookidooException],
    ) -> None:
        """Test parse exceptions."""
        mocked.post(
            "https://cookidoo.ch/shopping/de-CH/additional-items/remove",
            status=status,
            body="not json",
            content_type="application/json",
        )

        with pytest.raises(exception):
            await cookidoo.remove_additional_items(
                ["01JBQGDMRMR7RJW1C8AWDGD6YP", "01JBQGDMRNHAM7AMCR6YKPYKJQ"]
            )


class TestEditAdditionalItemsOwnership:
    """Tests for edit_additional_items_ownership method."""

    async def test_edit_additional_items_ownership(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for edit_additional_items_ownership."""

        mocked.post(
            "https://cookidoo.ch/shopping/de-CH/additional-items/ownership/edit",
            payload=COOKIDOO_TEST_RESPONSE_EDIT_ADDITIONAL_ITEMS_OWNERSHIP,
            status=HTTPStatus.OK,
        )

        data = await cookidoo.edit_additional_items_ownership(
            [
                CookidooAdditionalItem(
                    id="01JBQGMGMY4KD9ZGTKAS6GQME0",
                    name="Fisch",
                    is_owned=True,
                )
            ]
        )
        assert data
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0].is_owned

    @pytest.mark.parametrize(
        "exception",
        [
            TimeoutError,
            ClientError,
        ],
    )
    async def test_request_exception(
        self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception
    ) -> None:
        """Test request exceptions."""

        mocked.post(
            "https://cookidoo.ch/shopping/de-CH/additional-items/ownership/edit",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.edit_additional_items_ownership(
                [
                    CookidooAdditionalItem(
                        id="01JBQGMGMY4KD9ZGTKAS6GQME0",
                        name="Fisch",
                        is_owned=True,
                    )
                ]
            )

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.post(
            "https://cookidoo.ch/shopping/de-CH/additional-items/ownership/edit",
            status=HTTPStatus.UNAUTHORIZED,
            payload={"error_description": ""},
        )
        with pytest.raises(CookidooAuthException):
            await cookidoo.edit_additional_items_ownership(
                [
                    CookidooAdditionalItem(
                        id="01JBQGMGMY4KD9ZGTKAS6GQME0",
                        name="Fisch",
                        is_owned=True,
                    )
                ]
            )

    @pytest.mark.parametrize(
        ("status", "exception"),
        [
            (HTTPStatus.OK, CookidooParseException),
            (HTTPStatus.UNAUTHORIZED, CookidooAuthException),
        ],
    )
    async def test_parse_exception(
        self,
        mocked: aioresponses,
        cookidoo: Cookidoo,
        status: HTTPStatus,
        exception: type[CookidooException],
    ) -> None:
        """Test parse exceptions."""
        mocked.post(
            "https://cookidoo.ch/shopping/de-CH/additional-items/ownership/edit",
            status=status,
            body="not json",
            content_type="application/json",
        )

        with pytest.raises(exception):
            await cookidoo.edit_additional_items_ownership(
                [
                    CookidooAdditionalItem(
                        id="01JBQGMGMY4KD9ZGTKAS6GQME0",
                        name="Fisch",
                        is_owned=True,
                    )
                ]
            )


class TestEditAdditionalItems:
    """Tests for edit_additional_items method."""

    async def test_edit_additional_items(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for edit_additional_items."""

        mocked.post(
            "https://cookidoo.ch/shopping/de-CH/additional-items/edit",
            payload=COOKIDOO_TEST_RESPONSE_EDIT_ADDITIONAL_ITEMS,
            status=HTTPStatus.OK,
        )

        data = await cookidoo.edit_additional_items(
            [
                CookidooAdditionalItem(
                    id="01JBQGT72WP8Z31VCPQPT5VC6F",
                    name="Vogel",
                    is_owned=True,
                )
            ]
        )
        assert data
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0].name == "Vogel"

    @pytest.mark.parametrize(
        "exception",
        [
            TimeoutError,
            ClientError,
        ],
    )
    async def test_request_exception(
        self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception
    ) -> None:
        """Test request exceptions."""

        mocked.post(
            "https://cookidoo.ch/shopping/de-CH/additional-items/edit",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.edit_additional_items(
                [
                    CookidooAdditionalItem(
                        id="01JBQGT72WP8Z31VCPQPT5VC6F",
                        name="Vogel",
                        is_owned=True,
                    )
                ]
            )

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.post(
            "https://cookidoo.ch/shopping/de-CH/additional-items/edit",
            status=HTTPStatus.UNAUTHORIZED,
            payload={"error_description": ""},
        )
        with pytest.raises(CookidooAuthException):
            await cookidoo.edit_additional_items(
                [
                    CookidooAdditionalItem(
                        id="01JBQGT72WP8Z31VCPQPT5VC6F",
                        name="Vogel",
                        is_owned=True,
                    )
                ]
            )

    @pytest.mark.parametrize(
        ("status", "exception"),
        [
            (HTTPStatus.OK, CookidooParseException),
            (HTTPStatus.UNAUTHORIZED, CookidooAuthException),
        ],
    )
    async def test_parse_exception(
        self,
        mocked: aioresponses,
        cookidoo: Cookidoo,
        status: HTTPStatus,
        exception: type[CookidooException],
    ) -> None:
        """Test parse exceptions."""
        mocked.post(
            "https://cookidoo.ch/shopping/de-CH/additional-items/edit",
            status=status,
            body="not json",
            content_type="application/json",
        )

        with pytest.raises(exception):
            await cookidoo.edit_additional_items(
                [
                    CookidooAdditionalItem(
                        id="01JBQGT72WP8Z31VCPQPT5VC6F",
                        name="Vogel",
                        is_owned=True,
                    )
                ]
            )


class TestClearShoppingList:
    """Tests for clear_shopping_list method."""

    async def test_clear_shopping_list(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for clear_shopping_list."""

        mocked.delete(
            "https://cookidoo.ch/shopping/de-CH",
            payload=None,
            status=HTTPStatus.OK,
        )

        await cookidoo.clear_shopping_list()

    @pytest.mark.parametrize(
        "exception",
        [
            TimeoutError,
            ClientError,
        ],
    )
    async def test_request_exception(
        self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception
    ) -> None:
        """Test request exceptions."""

        mocked.delete(
            "https://cookidoo.ch/shopping/de-CH",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.clear_shopping_list()

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.delete(
            "https://cookidoo.ch/shopping/de-CH",
            status=HTTPStatus.UNAUTHORIZED,
            payload={"error_description": ""},
        )
        with pytest.raises(CookidooAuthException):
            await cookidoo.clear_shopping_list()

    @pytest.mark.parametrize(
        ("status", "exception"),
        [
            # (HTTPStatus.OK, CookidooParseException), # There is nothing to parse
            (HTTPStatus.UNAUTHORIZED, CookidooAuthException),
        ],
    )
    async def test_parse_exception(
        self,
        mocked: aioresponses,
        cookidoo: Cookidoo,
        status: HTTPStatus,
        exception: type[CookidooException],
    ) -> None:
        """Test parse exceptions."""
        mocked.delete(
            "https://cookidoo.ch/shopping/de-CH",
            status=status,
            body="not json",
            content_type="application/json",
        )

        with pytest.raises(exception):
            await cookidoo.clear_shopping_list()


class TestCountManagedLists:
    """Tests for count_managed_lists method."""

    async def test_count_managed_lists(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for count_managed_lists."""

        mocked.get(
            "https://cookidoo.ch/organize/de-CH/api/managed-list",
            payload=COOKIDOO_TEST_RESPONSE_GET_MANAGED_COLLECTIONS,
            status=HTTPStatus.OK,
        )

        count_recipes, count_pages = await cookidoo.count_managed_collections()
        assert count_recipes == 1
        assert count_pages == 1

    @pytest.mark.parametrize(
        "exception",
        [
            TimeoutError,
            ClientError,
        ],
    )
    async def test_request_exception(
        self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception
    ) -> None:
        """Test request exceptions."""

        mocked.get(
            "https://cookidoo.ch/organize/de-CH/api/managed-list",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.count_managed_collections()

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.get(
            "https://cookidoo.ch/organize/de-CH/api/managed-list",
            status=HTTPStatus.UNAUTHORIZED,
            payload={"error_description": ""},
        )
        with pytest.raises(CookidooAuthException):
            await cookidoo.count_managed_collections()

    @pytest.mark.parametrize(
        ("status", "exception"),
        [
            (HTTPStatus.OK, CookidooParseException),
            (HTTPStatus.UNAUTHORIZED, CookidooAuthException),
        ],
    )
    async def test_parse_exception(
        self,
        mocked: aioresponses,
        cookidoo: Cookidoo,
        status: HTTPStatus,
        exception: type[CookidooException],
    ) -> None:
        """Test parse exceptions."""
        mocked.get(
            "https://cookidoo.ch/organize/de-CH/api/managed-list",
            status=status,
            body="not json",
            content_type="application/json",
        )

        with pytest.raises(exception):
            await cookidoo.count_managed_collections()


class TestGetManagedLists:
    """Tests for get_managed_lists method."""

    async def test_get_managed_lists(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for get_managed_lists."""

        mocked.get(
            "https://cookidoo.ch/organize/de-CH/api/managed-list?page=0",
            payload=COOKIDOO_TEST_RESPONSE_GET_MANAGED_COLLECTIONS,
            status=HTTPStatus.OK,
        )

        data = await cookidoo.get_managed_collections()
        assert data
        assert isinstance(data, list)
        assert len(data) == 1

    @pytest.mark.parametrize(
        "exception",
        [
            TimeoutError,
            ClientError,
        ],
    )
    async def test_request_exception(
        self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception
    ) -> None:
        """Test request exceptions."""

        mocked.get(
            "https://cookidoo.ch/organize/de-CH/api/managed-list?page=0",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.get_managed_collections()

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.get(
            "https://cookidoo.ch/organize/de-CH/api/managed-list?page=0",
            status=HTTPStatus.UNAUTHORIZED,
            payload={"error_description": ""},
        )
        with pytest.raises(CookidooAuthException):
            await cookidoo.get_managed_collections()

    @pytest.mark.parametrize(
        ("status", "exception"),
        [
            (HTTPStatus.OK, CookidooParseException),
            (HTTPStatus.UNAUTHORIZED, CookidooAuthException),
        ],
    )
    async def test_parse_exception(
        self,
        mocked: aioresponses,
        cookidoo: Cookidoo,
        status: HTTPStatus,
        exception: type[CookidooException],
    ) -> None:
        """Test parse exceptions."""
        mocked.get(
            "https://cookidoo.ch/organize/de-CH/api/managed-list?page=0",
            status=status,
            body="not json",
            content_type="application/json",
        )

        with pytest.raises(exception):
            await cookidoo.get_managed_collections()


class TestAddManagedCollection:
    """Tests for add_managed_collection method."""

    async def test_add_managed_collection(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for add_managed_collection."""

        mocked.post(
            "https://cookidoo.ch/organize/de-CH/api/managed-list",
            payload=COOKIDOO_TEST_RESPONSE_ADD_MANAGED_COLLECTION,
            status=HTTPStatus.OK,
        )

        data = await cookidoo.add_managed_collection("col500561")
        assert data
        assert data.id == "col500561"

    @pytest.mark.parametrize(
        "exception",
        [
            TimeoutError,
            ClientError,
        ],
    )
    async def test_request_exception(
        self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception
    ) -> None:
        """Test request exceptions."""

        mocked.post(
            "https://cookidoo.ch/organize/de-CH/api/managed-list",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.add_managed_collection("col500561")

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.post(
            "https://cookidoo.ch/organize/de-CH/api/managed-list",
            status=HTTPStatus.UNAUTHORIZED,
            payload={"error_description": ""},
        )
        with pytest.raises(CookidooAuthException):
            await cookidoo.add_managed_collection("col500561")

    @pytest.mark.parametrize(
        ("status", "exception"),
        [
            (HTTPStatus.OK, CookidooParseException),
            (HTTPStatus.UNAUTHORIZED, CookidooAuthException),
        ],
    )
    async def test_parse_exception(
        self,
        mocked: aioresponses,
        cookidoo: Cookidoo,
        status: HTTPStatus,
        exception: type[CookidooException],
    ) -> None:
        """Test parse exceptions."""
        mocked.post(
            "https://cookidoo.ch/organize/de-CH/api/managed-list",
            status=status,
            body="not json",
            content_type="application/json",
        )

        with pytest.raises(exception):
            await cookidoo.add_managed_collection("col500561")


class TestRemoveManagedCollection:
    """Tests for remove_managed_collection method."""

    async def test_remove_managed_collection(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for remove_managed_collection."""

        mocked.delete(
            "https://cookidoo.ch/organize/de-CH/api/managed-list/col500561",
            payload=None,
            status=HTTPStatus.OK,
        )

        await cookidoo.remove_managed_collection("col500561")

    @pytest.mark.parametrize(
        "exception",
        [
            TimeoutError,
            ClientError,
        ],
    )
    async def test_request_exception(
        self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception
    ) -> None:
        """Test request exceptions."""

        mocked.delete(
            "https://cookidoo.ch/organize/de-CH/api/managed-list/col500561",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.remove_managed_collection("col500561")

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.delete(
            "https://cookidoo.ch/organize/de-CH/api/managed-list/col500561",
            status=HTTPStatus.UNAUTHORIZED,
            payload={"error_description": ""},
        )
        with pytest.raises(CookidooAuthException):
            await cookidoo.remove_managed_collection("col500561")

    @pytest.mark.parametrize(
        ("status", "exception"),
        [
            # (HTTPStatus.OK, CookidooParseException), # There is nothing to parse
            (HTTPStatus.UNAUTHORIZED, CookidooAuthException),
        ],
    )
    async def test_parse_exception(
        self,
        mocked: aioresponses,
        cookidoo: Cookidoo,
        status: HTTPStatus,
        exception: type[CookidooException],
    ) -> None:
        """Test parse exceptions."""
        mocked.delete(
            "https://cookidoo.ch/organize/de-CH/api/managed-list/col500561",
            status=status,
            body="not json",
            content_type="application/json",
        )

        with pytest.raises(exception):
            await cookidoo.remove_managed_collection("col500561")


class TestCountCustomLists:
    """Tests for count_custom_lists method."""

    async def test_count_custom_lists(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for count_custom_lists."""

        mocked.get(
            "https://cookidoo.ch/organize/de-CH/api/custom-list",
            payload=COOKIDOO_TEST_RESPONSE_GET_CUSTOM_COLLECTIONS,
            status=HTTPStatus.OK,
        )

        count_recipes, count_pages = await cookidoo.count_custom_collections()
        assert count_recipes == 1
        assert count_pages == 1

    @pytest.mark.parametrize(
        "exception",
        [
            TimeoutError,
            ClientError,
        ],
    )
    async def test_request_exception(
        self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception
    ) -> None:
        """Test request exceptions."""

        mocked.get(
            "https://cookidoo.ch/organize/de-CH/api/custom-list",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.count_custom_collections()

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.get(
            "https://cookidoo.ch/organize/de-CH/api/custom-list",
            status=HTTPStatus.UNAUTHORIZED,
            payload={"error_description": ""},
        )
        with pytest.raises(CookidooAuthException):
            await cookidoo.count_custom_collections()

    @pytest.mark.parametrize(
        ("status", "exception"),
        [
            (HTTPStatus.OK, CookidooParseException),
            (HTTPStatus.UNAUTHORIZED, CookidooAuthException),
        ],
    )
    async def test_parse_exception(
        self,
        mocked: aioresponses,
        cookidoo: Cookidoo,
        status: HTTPStatus,
        exception: type[CookidooException],
    ) -> None:
        """Test parse exceptions."""
        mocked.get(
            "https://cookidoo.ch/organize/de-CH/api/custom-list",
            status=status,
            body="not json",
            content_type="application/json",
        )

        with pytest.raises(exception):
            await cookidoo.count_custom_collections()


class TestGetCustomLists:
    """Tests for get_custom_lists method."""

    async def test_get_custom_lists(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for get_custom_lists."""

        mocked.get(
            "https://cookidoo.ch/organize/de-CH/api/custom-list?page=0",
            payload=COOKIDOO_TEST_RESPONSE_GET_CUSTOM_COLLECTIONS,
            status=HTTPStatus.OK,
        )

        data = await cookidoo.get_custom_collections()
        assert data
        assert isinstance(data, list)
        assert len(data) == 1

    @pytest.mark.parametrize(
        "exception",
        [
            TimeoutError,
            ClientError,
        ],
    )
    async def test_request_exception(
        self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception
    ) -> None:
        """Test request exceptions."""

        mocked.get(
            "https://cookidoo.ch/organize/de-CH/api/custom-list?page=0",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.get_custom_collections()

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.get(
            "https://cookidoo.ch/organize/de-CH/api/custom-list?page=0",
            status=HTTPStatus.UNAUTHORIZED,
            payload={"error_description": ""},
        )
        with pytest.raises(CookidooAuthException):
            await cookidoo.get_custom_collections()

    @pytest.mark.parametrize(
        ("status", "exception"),
        [
            (HTTPStatus.OK, CookidooParseException),
            (HTTPStatus.UNAUTHORIZED, CookidooAuthException),
        ],
    )
    async def test_parse_exception(
        self,
        mocked: aioresponses,
        cookidoo: Cookidoo,
        status: HTTPStatus,
        exception: type[CookidooException],
    ) -> None:
        """Test parse exceptions."""
        mocked.get(
            "https://cookidoo.ch/organize/de-CH/api/custom-list?page=0",
            status=status,
            body="not json",
            content_type="application/json",
        )

        with pytest.raises(exception):
            await cookidoo.get_custom_collections()


class TestAddCustomCollection:
    """Tests for add_custom_collection method."""

    async def test_add_custom_collection(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for add_custom_collection."""

        mocked.post(
            "https://cookidoo.ch/organize/de-CH/api/custom-list",
            payload=COOKIDOO_TEST_RESPONSE_ADD_CUSTOM_COLLECTION,
            status=HTTPStatus.OK,
        )

        data = await cookidoo.add_custom_collection("Testliste")
        assert data
        assert data.id == "01JC1SRPRSW0SHE0AK8GCASABX"
        assert data.name == "Testliste"

    @pytest.mark.parametrize(
        "exception",
        [
            TimeoutError,
            ClientError,
        ],
    )
    async def test_request_exception(
        self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception
    ) -> None:
        """Test request exceptions."""

        mocked.post(
            "https://cookidoo.ch/organize/de-CH/api/custom-list",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.add_custom_collection("TEST_COLLECTION")

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.post(
            "https://cookidoo.ch/organize/de-CH/api/custom-list",
            status=HTTPStatus.UNAUTHORIZED,
            payload={"error_description": ""},
        )
        with pytest.raises(CookidooAuthException):
            await cookidoo.add_custom_collection("TEST_COLLECTION")

    @pytest.mark.parametrize(
        ("status", "exception"),
        [
            (HTTPStatus.OK, CookidooParseException),
            (HTTPStatus.UNAUTHORIZED, CookidooAuthException),
        ],
    )
    async def test_parse_exception(
        self,
        mocked: aioresponses,
        cookidoo: Cookidoo,
        status: HTTPStatus,
        exception: type[CookidooException],
    ) -> None:
        """Test parse exceptions."""
        mocked.post(
            "https://cookidoo.ch/organize/de-CH/api/custom-list",
            status=status,
            body="not json",
            content_type="application/json",
        )

        with pytest.raises(exception):
            await cookidoo.add_custom_collection("TEST_COLLECTION")


class TestRemoveCustomCollection:
    """Tests for remove_custom_collection method."""

    async def test_remove_custom_collection(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for remove_custom_collection."""

        mocked.delete(
            "https://cookidoo.ch/organize/de-CH/api/custom-list/01JC1SRPRSW0SHE0AK8GCASABX",
            payload=None,
            status=HTTPStatus.OK,
        )

        await cookidoo.remove_custom_collection("01JC1SRPRSW0SHE0AK8GCASABX")

    @pytest.mark.parametrize(
        "exception",
        [
            TimeoutError,
            ClientError,
        ],
    )
    async def test_request_exception(
        self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception
    ) -> None:
        """Test request exceptions."""

        mocked.delete(
            "https://cookidoo.ch/organize/de-CH/api/custom-list/01JC1SRPRSW0SHE0AK8GCASABX",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.remove_custom_collection("01JC1SRPRSW0SHE0AK8GCASABX")

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.delete(
            "https://cookidoo.ch/organize/de-CH/api/custom-list/01JC1SRPRSW0SHE0AK8GCASABX",
            status=HTTPStatus.UNAUTHORIZED,
            payload={"error_description": ""},
        )
        with pytest.raises(CookidooAuthException):
            await cookidoo.remove_custom_collection("01JC1SRPRSW0SHE0AK8GCASABX")

    @pytest.mark.parametrize(
        ("status", "exception"),
        [
            # (HTTPStatus.OK, CookidooParseException), # There is nothing to parse
            (HTTPStatus.UNAUTHORIZED, CookidooAuthException),
        ],
    )
    async def test_parse_exception(
        self,
        mocked: aioresponses,
        cookidoo: Cookidoo,
        status: HTTPStatus,
        exception: type[CookidooException],
    ) -> None:
        """Test parse exceptions."""
        mocked.delete(
            "https://cookidoo.ch/organize/de-CH/api/custom-list/01JC1SRPRSW0SHE0AK8GCASABX",
            status=status,
            body="not json",
            content_type="application/json",
        )

        with pytest.raises(exception):
            await cookidoo.remove_custom_collection("01JC1SRPRSW0SHE0AK8GCASABX")


class TestAddRecipesToCustomCollection:
    """Tests for add_recipes_to_custom_collection method."""

    async def test_add_recipes_to_custom_collection(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for add_recipes_to_custom_collection."""

        mocked.put(
            "https://cookidoo.ch/organize/de-CH/api/custom-list/01JC1SRPRSW0SHE0AK8GCASABX",
            payload=COOKIDOO_TEST_RESPONSE_ADD_RECIPES_TO_CUSTOM_COLLECTION,
            status=HTTPStatus.OK,
        )

        data = await cookidoo.add_recipes_to_custom_collection(
            "01JC1SRPRSW0SHE0AK8GCASABX", ["r907015"]
        )
        assert data
        assert data.id == "01JC1SRPRSW0SHE0AK8GCASABX"
        assert data.chapters[0].recipes[0].id == "r907015"

    @pytest.mark.parametrize(
        "exception",
        [
            TimeoutError,
            ClientError,
        ],
    )
    async def test_request_exception(
        self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception
    ) -> None:
        """Test request exceptions."""

        mocked.put(
            "https://cookidoo.ch/organize/de-CH/api/custom-list/01JC1SRPRSW0SHE0AK8GCASABX",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.add_recipes_to_custom_collection(
                "01JC1SRPRSW0SHE0AK8GCASABX", ["r907015"]
            )

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.put(
            "https://cookidoo.ch/organize/de-CH/api/custom-list/01JC1SRPRSW0SHE0AK8GCASABX",
            status=HTTPStatus.UNAUTHORIZED,
            payload={"error_description": ""},
        )
        with pytest.raises(CookidooAuthException):
            await cookidoo.add_recipes_to_custom_collection(
                "01JC1SRPRSW0SHE0AK8GCASABX", ["r907015"]
            )

    @pytest.mark.parametrize(
        ("status", "exception"),
        [
            (HTTPStatus.OK, CookidooParseException),
            (HTTPStatus.UNAUTHORIZED, CookidooAuthException),
        ],
    )
    async def test_parse_exception(
        self,
        mocked: aioresponses,
        cookidoo: Cookidoo,
        status: HTTPStatus,
        exception: type[CookidooException],
    ) -> None:
        """Test parse exceptions."""
        mocked.put(
            "https://cookidoo.ch/organize/de-CH/api/custom-list/01JC1SRPRSW0SHE0AK8GCASABX",
            status=status,
            body="not json",
            content_type="application/json",
        )

        with pytest.raises(exception):
            await cookidoo.add_recipes_to_custom_collection(
                "01JC1SRPRSW0SHE0AK8GCASABX", ["r907015"]
            )


class TestRemoveRecipeFromCustomCollection:
    """Tests for remove_recipe_from_custom_collection method."""

    async def test_remove_recipe_from_custom_collection(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for remove_recipe_from_custom_collection."""

        mocked.delete(
            "https://cookidoo.ch/organize/de-CH/api/custom-list/01JC1SRPRSW0SHE0AK8GCASABX/recipes/r907015",
            payload=COOKIDOO_TEST_RESPONSE_REMOVE_RECIPE_FROM_CUSTOM_COLLECTION,
            status=HTTPStatus.OK,
        )

        data = await cookidoo.remove_recipe_from_custom_collection(
            "01JC1SRPRSW0SHE0AK8GCASABX", "r907015"
        )
        assert data
        assert data.id == "01JC1SRPRSW0SHE0AK8GCASABX"
        assert len(data.chapters[0].recipes) == 0

    @pytest.mark.parametrize(
        "exception",
        [
            TimeoutError,
            ClientError,
        ],
    )
    async def test_request_exception(
        self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception
    ) -> None:
        """Test request exceptions."""

        mocked.delete(
            "https://cookidoo.ch/organize/de-CH/api/custom-list/01JC1SRPRSW0SHE0AK8GCASABX/recipes/r907015",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.remove_recipe_from_custom_collection(
                "01JC1SRPRSW0SHE0AK8GCASABX", "r907015"
            )

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.delete(
            "https://cookidoo.ch/organize/de-CH/api/custom-list/01JC1SRPRSW0SHE0AK8GCASABX/recipes/r907015",
            status=HTTPStatus.UNAUTHORIZED,
            payload={"error_description": ""},
        )
        with pytest.raises(CookidooAuthException):
            await cookidoo.remove_recipe_from_custom_collection(
                "01JC1SRPRSW0SHE0AK8GCASABX", "r907015"
            )

    @pytest.mark.parametrize(
        ("status", "exception"),
        [
            (HTTPStatus.OK, CookidooParseException),
            (HTTPStatus.UNAUTHORIZED, CookidooAuthException),
        ],
    )
    async def test_parse_exception(
        self,
        mocked: aioresponses,
        cookidoo: Cookidoo,
        status: HTTPStatus,
        exception: type[CookidooException],
    ) -> None:
        """Test parse exceptions."""
        mocked.delete(
            "https://cookidoo.ch/organize/de-CH/api/custom-list/01JC1SRPRSW0SHE0AK8GCASABX/recipes/r907015",
            status=status,
            body="not json",
            content_type="application/json",
        )

        with pytest.raises(exception):
            await cookidoo.remove_recipe_from_custom_collection(
                "01JC1SRPRSW0SHE0AK8GCASABX", "r907015"
            )


class TestGetCalendarWeek:
    """Tests for get_calendar_week method."""

    async def test_get_calendar_week(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for get_calendar_week."""

        mocked.get(
            "https://cookidoo.ch/planning/de-CH/api/my-week/2025-03-03",
            payload=COOKIDOO_TEST_RESPONSE_CALENDAR_WEEK,
            status=HTTPStatus.OK,
        )

        data = await cookidoo.get_recipes_in_calendar_week(
            datetime.fromisoformat("2025-03-03").date()
        )
        assert data
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0].id == "2025-03-04"
        assert data[0].recipes[0].id == "r214846"
        assert data[1].id == "2025-03-05"
        assert data[1].recipes[0].id == "r338888"

    @pytest.mark.parametrize(
        "exception",
        [
            TimeoutError,
            ClientError,
        ],
    )
    async def test_request_exception(
        self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception
    ) -> None:
        """Test request exceptions."""

        mocked.get(
            "https://cookidoo.ch/planning/de-CH/api/my-week/2025-03-03",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.get_recipes_in_calendar_week(
                datetime.fromisoformat("2025-03-03").date()
            )

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.get(
            "https://cookidoo.ch/planning/de-CH/api/my-week/2025-03-03",
            status=HTTPStatus.UNAUTHORIZED,
            payload={"error_description": ""},
        )
        with pytest.raises(CookidooAuthException):
            await cookidoo.get_recipes_in_calendar_week(
                datetime.fromisoformat("2025-03-03").date()
            )

    @pytest.mark.parametrize(
        ("status", "exception"),
        [
            (HTTPStatus.OK, CookidooParseException),
            (HTTPStatus.UNAUTHORIZED, CookidooAuthException),
        ],
    )
    async def test_parse_exception(
        self,
        mocked: aioresponses,
        cookidoo: Cookidoo,
        status: HTTPStatus,
        exception: type[CookidooException],
    ) -> None:
        """Test parse exceptions."""
        mocked.get(
            "https://cookidoo.ch/planning/de-CH/api/my-week/2025-03-03",
            status=status,
            body="not json",
            content_type="application/json",
        )

        with pytest.raises(exception):
            await cookidoo.get_recipes_in_calendar_week(
                datetime.fromisoformat("2025-03-03").date()
            )


class TestAddRecipesToCalendar:
    """Tests for add_recipes_to_calendar method."""

    async def test_add_recipes_to_custom_collection(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for add_recipes_to_calendar."""

        mocked.put(
            "https://cookidoo.ch/planning/de-CH/api/my-day",
            payload=COOKIDOO_TEST_RESPONSE_ADD_RECIPES_TO_CALENDAR,
            status=HTTPStatus.OK,
        )

        data = await cookidoo.add_recipes_to_calendar(
            datetime.fromisoformat("2025-03-04").date(), ["r214846"]
        )
        assert data
        assert data.id == "2025-03-04"
        assert data.recipes[0].id == "r214846"

    @pytest.mark.parametrize(
        "exception",
        [
            TimeoutError,
            ClientError,
        ],
    )
    async def test_request_exception(
        self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception
    ) -> None:
        """Test request exceptions."""

        mocked.put(
            "https://cookidoo.ch/planning/de-CH/api/my-day",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.add_recipes_to_calendar(
                datetime.fromisoformat("2025-03-04").date(), ["r214846"]
            )

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.put(
            "https://cookidoo.ch/planning/de-CH/api/my-day",
            status=HTTPStatus.UNAUTHORIZED,
            payload={"error_description": ""},
        )
        with pytest.raises(CookidooAuthException):
            await cookidoo.add_recipes_to_calendar(
                datetime.fromisoformat("2025-03-04").date(), ["r214846"]
            )

    @pytest.mark.parametrize(
        ("status", "exception"),
        [
            (HTTPStatus.OK, CookidooParseException),
            (HTTPStatus.UNAUTHORIZED, CookidooAuthException),
        ],
    )
    async def test_parse_exception(
        self,
        mocked: aioresponses,
        cookidoo: Cookidoo,
        status: HTTPStatus,
        exception: type[CookidooException],
    ) -> None:
        """Test parse exceptions."""
        mocked.put(
            "https://cookidoo.ch/planning/de-CH/api/my-day",
            status=status,
            body="not json",
            content_type="application/json",
        )

        with pytest.raises(exception):
            await cookidoo.add_recipes_to_calendar(
                datetime.fromisoformat("2025-03-04").date(), ["r214846"]
            )


class TestRemoveRecipeFromCalendar:
    """Tests for remove_recipe_from_calendar method."""

    async def test_remove_recipe_from_calendar(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for remove_recipe_from_calendar."""

        mocked.delete(
            "https://cookidoo.ch/planning/de-CH/api/my-day/2025-03-04/recipes/r214846",
            payload=COOKIDOO_TEST_RESPONSE_REMOVE_RECIPE_FROM_CALENDAR,
            status=HTTPStatus.OK,
        )

        data = await cookidoo.remove_recipe_from_calendar(
            datetime.fromisoformat("2025-03-04").date(), "r214846"
        )
        assert data
        assert data.id == "2025-03-04"
        assert data.recipes[0].id == "r214846"

    async def test_remove_last_recipe_from_calendar(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for remove_recipe_from_calendar when the day becomes empty."""

        mocked.delete(
            "https://cookidoo.ch/planning/de-CH/api/my-day/2025-03-04/recipes/r214846",
            payload={"message": "Recipe Waffles was removed!", "content": None},
            status=HTTPStatus.OK,
        )

        data = await cookidoo.remove_recipe_from_calendar(
            datetime.fromisoformat("2025-03-04").date(), "r214846"
        )
        assert data
        assert data.id == "2025-03-04"
        assert data.recipes == []

    @pytest.mark.parametrize(
        "exception",
        [
            TimeoutError,
            ClientError,
        ],
    )
    async def test_request_exception(
        self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception
    ) -> None:
        """Test request exceptions."""

        mocked.delete(
            "https://cookidoo.ch/planning/de-CH/api/my-day/2025-03-04/recipes/r214846",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.remove_recipe_from_calendar(
                datetime.fromisoformat("2025-03-04").date(), "r214846"
            )

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.delete(
            "https://cookidoo.ch/planning/de-CH/api/my-day/2025-03-04/recipes/r214846",
            status=HTTPStatus.UNAUTHORIZED,
            payload={"error_description": ""},
        )
        with pytest.raises(CookidooAuthException):
            await cookidoo.remove_recipe_from_calendar(
                datetime.fromisoformat("2025-03-04").date(), "r214846"
            )

    @pytest.mark.parametrize(
        ("status", "exception"),
        [
            (HTTPStatus.OK, CookidooParseException),
            (HTTPStatus.UNAUTHORIZED, CookidooAuthException),
        ],
    )
    async def test_parse_exception(
        self,
        mocked: aioresponses,
        cookidoo: Cookidoo,
        status: HTTPStatus,
        exception: type[CookidooException],
    ) -> None:
        """Test parse exceptions."""
        mocked.delete(
            "https://cookidoo.ch/planning/de-CH/api/my-day/2025-03-04/recipes/r214846",
            status=status,
            body="not json",
            content_type="application/json",
        )

        with pytest.raises(exception):
            await cookidoo.remove_recipe_from_calendar(
                datetime.fromisoformat("2025-03-04").date(), "r214846"
            )


class TestAddCustomRecipesToCalendar:
    """Tests for add_custom_recipes_to_calendar method."""

    async def test_add_custom_recipes_to_custom_collection(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for add_custom_recipes_to_calendar."""

        mocked.put(
            "https://cookidoo.ch/planning/de-CH/api/my-day",
            payload=COOKIDOO_TEST_RESPONSE_ADD_CUSTOM_RECIPES_TO_CALENDAR,
            status=HTTPStatus.OK,
        )

        data = await cookidoo.add_custom_recipes_to_calendar(
            datetime.fromisoformat("2025-08-11").date(), ["01K2CTJ9Y1BABRG5MXK44CFZS4"]
        )
        assert data
        assert data.id == "2025-08-11"

    @pytest.mark.parametrize(
        "exception",
        [
            TimeoutError,
            ClientError,
        ],
    )
    async def test_request_exception(
        self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception
    ) -> None:
        """Test request exceptions."""

        mocked.put(
            "https://cookidoo.ch/planning/de-CH/api/my-day",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.add_custom_recipes_to_calendar(
                datetime.fromisoformat("2025-08-11").date(),
                ["01K2CTJ9Y1BABRG5MXK44CFZS4"],
            )

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.put(
            "https://cookidoo.ch/planning/de-CH/api/my-day",
            status=HTTPStatus.UNAUTHORIZED,
            payload={"error_description": ""},
        )
        with pytest.raises(CookidooAuthException):
            await cookidoo.add_custom_recipes_to_calendar(
                datetime.fromisoformat("2025-08-11").date(),
                ["01K2CTJ9Y1BABRG5MXK44CFZS4"],
            )

    @pytest.mark.parametrize(
        ("status", "exception"),
        [
            (HTTPStatus.OK, CookidooParseException),
            (HTTPStatus.UNAUTHORIZED, CookidooAuthException),
        ],
    )
    async def test_parse_exception(
        self,
        mocked: aioresponses,
        cookidoo: Cookidoo,
        status: HTTPStatus,
        exception: type[CookidooException],
    ) -> None:
        """Test parse exceptions."""
        mocked.put(
            "https://cookidoo.ch/planning/de-CH/api/my-day",
            status=status,
            body="not json",
            content_type="application/json",
        )

        with pytest.raises(exception):
            await cookidoo.add_custom_recipes_to_calendar(
                datetime.fromisoformat("2025-08-11").date(),
                ["01K2CTJ9Y1BABRG5MXK44CFZS4"],
            )


class TestRemoveCustomRecipeFromCalendar:
    """Tests for remove_custom_recipe_from_calendar method."""

    async def test_remove_custom_recipe_from_calendar(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for remove_custom_recipe_from_calendar."""

        mocked.delete(
            "https://cookidoo.ch/planning/de-CH/api/my-day/2025-08-11/recipes/r214846?recipeSource=CUSTOMER",
            payload=COOKIDOO_TEST_RESPONSE_REMOVE_CUSTOM_RECIPE_FROM_CALENDAR,
            status=HTTPStatus.OK,
        )

        data = await cookidoo.remove_custom_recipe_from_calendar(
            datetime.fromisoformat("2025-08-11").date(), "r214846"
        )
        assert data
        assert data.id == "2025-08-11"

    async def test_remove_last_custom_recipe_from_calendar(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test remove_custom_recipe_from_calendar when the day becomes empty."""

        mocked.delete(
            "https://cookidoo.ch/planning/de-CH/api/my-day/2025-08-11/recipes/r214846?recipeSource=CUSTOMER",
            payload={"message": "Recipe removed!", "content": None},
            status=HTTPStatus.OK,
        )

        data = await cookidoo.remove_custom_recipe_from_calendar(
            datetime.fromisoformat("2025-08-11").date(), "r214846"
        )
        assert data
        assert data.id == "2025-08-11"
        assert data.recipes == []

    @pytest.mark.parametrize(
        "exception",
        [
            TimeoutError,
            ClientError,
        ],
    )
    async def test_request_exception(
        self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception
    ) -> None:
        """Test request exceptions."""

        mocked.delete(
            "https://cookidoo.ch/planning/de-CH/api/my-day/2025-08-11/recipes/01K2CTJ9Y1BABRG5MXK44CFZS4?recipeSource=CUSTOMER",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.remove_custom_recipe_from_calendar(
                datetime.fromisoformat("2025-08-11").date(),
                "01K2CTJ9Y1BABRG5MXK44CFZS4",
            )

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.delete(
            "https://cookidoo.ch/planning/de-CH/api/my-day/2025-08-11/recipes/01K2CTJ9Y1BABRG5MXK44CFZS4?recipeSource=CUSTOMER",
            status=HTTPStatus.UNAUTHORIZED,
            payload={"error_description": ""},
        )
        with pytest.raises(CookidooAuthException):
            await cookidoo.remove_custom_recipe_from_calendar(
                datetime.fromisoformat("2025-08-11").date(),
                "01K2CTJ9Y1BABRG5MXK44CFZS4",
            )

    @pytest.mark.parametrize(
        ("status", "exception"),
        [
            (HTTPStatus.OK, CookidooParseException),
            (HTTPStatus.UNAUTHORIZED, CookidooAuthException),
        ],
    )
    async def test_parse_exception(
        self,
        mocked: aioresponses,
        cookidoo: Cookidoo,
        status: HTTPStatus,
        exception: type[CookidooException],
    ) -> None:
        """Test parse exceptions."""
        mocked.delete(
            "https://cookidoo.ch/planning/de-CH/api/my-day/2025-08-11/recipes/01K2CTJ9Y1BABRG5MXK44CFZS4?recipeSource=CUSTOMER",
            status=status,
            body="not json",
            content_type="application/json",
        )

        with pytest.raises(exception):
            await cookidoo.remove_custom_recipe_from_calendar(
                datetime.fromisoformat("2025-08-11").date(),
                "01K2CTJ9Y1BABRG5MXK44CFZS4",
            )


class TestRemoteMonitoring:
    """Tests for remote-monitoring (device management) methods."""

    MOBILE_HOME_URL = "https://cookidoo.ch/.well-known/mobile-home"
    RMI_CONFIG_URL = (
        "https://it.tmmobile.vorwerk-digital.com/rmi-config/.well-known/home"
    )
    DEVICES_URL = "https://iot-api.production-eu.cookidoo.vorwerk-digital.com/devices"
    REGISTER_URL = (
        "https://iot-api.production-eu.cookidoo.vorwerk-digital.com/device-token"
    )
    UNREGISTER_URL = "https://iot-api.production-eu.cookidoo.vorwerk-digital.com/token"

    def _mock_rmi_resolution(self, mocked: aioresponses) -> None:
        mocked.get(self.MOBILE_HOME_URL, payload=COOKIDOO_TEST_RESPONSE_MOBILE_HOME)
        mocked.get(self.RMI_CONFIG_URL, payload=COOKIDOO_TEST_RESPONSE_RMI_CONFIG)

    async def test_get_monitored_device_ids(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test listing monitorable device ids."""
        self._mock_rmi_resolution(mocked)
        mocked.get(self.DEVICES_URL, payload=COOKIDOO_TEST_RESPONSE_MONITORED_DEVICES)

        ids = await cookidoo.get_monitored_device_ids()
        assert ids == [
            "22e920b2d6184cec6c854cd005d6aa8fb851d7e783478b50f361ac8d1ab97bfe"
        ]

    async def test_get_monitored_device_ids_empty(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test listing when no device is currently monitorable."""
        self._mock_rmi_resolution(mocked)
        mocked.get(self.DEVICES_URL, payload=[])

        assert await cookidoo.get_monitored_device_ids() == []

    async def test_register_push_token(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test registering a push token."""
        self._mock_rmi_resolution(mocked)
        mocked.post(self.REGISTER_URL, payload={"message": "OK"})

        await cookidoo.register_push_token("fcm-token", "app-install-id")

    async def test_unregister_push_token(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test unregistering a push token."""
        self._mock_rmi_resolution(mocked)
        mocked.delete(self.UNREGISTER_URL, payload={"message": "OK"})

        await cookidoo.unregister_push_token("fcm-token")

    async def test_rmi_config_link_missing(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """A home doc without the rmi-config link raises."""
        mocked.get(self.MOBILE_HOME_URL, payload={"_links": {}})

        with pytest.raises(CookidooParseException, match="rmi-config link missing"):
            await cookidoo.get_monitored_device_ids()

    async def test_rmi_links_are_cached(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """The resolution walk runs once and is reused afterwards."""
        self._mock_rmi_resolution(mocked)
        mocked.get(self.DEVICES_URL, payload=[])
        mocked.get(self.DEVICES_URL, payload=[])

        await cookidoo.get_monitored_device_ids()
        await cookidoo.get_monitored_device_ids()

        # Only the first call walked mobile-home -> rmi-config.
        assert len(mocked.requests[("get", URL(self.MOBILE_HOME_URL))]) == 1
        assert len(mocked.requests[("get", URL(self.RMI_CONFIG_URL))]) == 1

    async def test_mobile_home_without_links(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """A home doc whose ``_links`` is not an object raises."""
        mocked.get(self.MOBILE_HOME_URL, payload={"_links": "not-an-object"})

        with pytest.raises(CookidooParseException, match="rmi-config link missing"):
            await cookidoo.get_monitored_device_ids()

    async def test_rmi_config_without_links(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """An rmi-config document without a ``_links`` object raises."""
        mocked.get(self.MOBILE_HOME_URL, payload=COOKIDOO_TEST_RESPONSE_MOBILE_HOME)
        mocked.get(self.RMI_CONFIG_URL, payload={"_links": "not-an-object"})

        with pytest.raises(CookidooParseException, match="during parsing"):
            await cookidoo.get_monitored_device_ids()

    async def test_rmi_links_accept_both_hal_shapes(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """A rel maps either to a bare href string or to a ``{"href": ...}``."""
        mocked.get(
            self.MOBILE_HOME_URL,
            payload={"_links": {"tmde2:rmi-config": self.RMI_CONFIG_URL}},
        )
        mocked.get(
            self.RMI_CONFIG_URL,
            payload={
                "_links": {
                    "rmi:devices": self.DEVICES_URL,
                    "rmi:unregister": {"href": self.UNREGISTER_URL},
                    "rmi:ignored": {"no-href": True},
                }
            },
        )
        mocked.get(self.DEVICES_URL, payload=[])

        assert await cookidoo.get_monitored_device_ids() == []

    @pytest.mark.parametrize(
        ("rel", "call", "args"),
        [
            ("rmi:devices", "get_monitored_device_ids", ()),
            ("rmi:register-token", "register_push_token", ("fcm-token", "install-id")),
            ("rmi:unregister", "unregister_push_token", ("fcm-token",)),
        ],
    )
    async def test_rmi_endpoint_link_missing(
        self,
        mocked: aioresponses,
        cookidoo: Cookidoo,
        rel: str,
        call: str,
        args: tuple[str, ...],
    ) -> None:
        """Each endpoint reports its own missing link rather than failing late."""
        links = {
            k: v
            for k, v in COOKIDOO_TEST_RESPONSE_RMI_CONFIG["_links"].items()
            if k != rel
        }
        mocked.get(self.MOBILE_HOME_URL, payload=COOKIDOO_TEST_RESPONSE_MOBILE_HOME)
        mocked.get(self.RMI_CONFIG_URL, payload={"_links": links})

        with pytest.raises(CookidooParseException, match=f"{rel} link missing"):
            await getattr(cookidoo, call)(*args)

    @pytest.mark.parametrize(
        ("field", "value", "attr", "expected"),
        [
            # _push_timestamp: unparseable and empty strings degrade to None
            ("completedDate", "not-a-date", "completed_at", None),
            ("completedDate", "", "completed_at", None),
            ("completedDate", None, "completed_at", None),
            ("completedDate", ["unexpected", "shape"], "completed_at", None),
            # _push_number: sentinels, comma decimals and native numbers
            ("secondaryInfo", "---", "target_temperature", None),
            ("secondaryInfo", "", "target_temperature", None),
            ("secondaryInfo", "not-a-number", "target_temperature", None),
            ("secondaryInfo", "37,5", "target_temperature", 37.5),
            ("secondaryInfo", 95, "target_temperature", 95.0),
            ("secondaryInfo", None, "target_temperature", None),
            # _push_bool: real bools pass through, strings are coerced
            ("isTimeEstimated", True, "is_time_estimated", True),
            ("isTimeEstimated", "yes", "is_time_estimated", True),
            ("isTimeEstimated", "FALSE", "is_time_estimated", False),
            ("isTimeEstimated", 1, "is_time_estimated", True),
        ],
    )
    def test_cooking_activity_from_push_field_parsing(
        self, field: str, value: object, attr: str, expected: object
    ) -> None:
        """Malformed or alternately-typed push fields degrade instead of raising."""
        payload = {**COOKIDOO_TEST_PUSH_COOKING_ACTIVITY, field: value}

        assert getattr(cooking_activity_from_push(payload), attr) == expected

    @pytest.mark.parametrize("remaining", ["600", 600])
    def test_cooking_activity_from_push_remaining_duration(
        self, remaining: object
    ) -> None:
        """``remainingDuration`` arrives as a string or an int; both are used."""
        payload = {
            **COOKIDOO_TEST_PUSH_COOKING_ACTIVITY,
            "remainingDuration": remaining,
        }

        assert cooking_activity_from_push(payload).remaining_seconds == 600

    def test_cooking_activity_from_push_remaining_duration_unparseable(self) -> None:
        """An unparseable duration falls back to deriving it from the finish time."""
        payload = {
            **COOKIDOO_TEST_PUSH_COOKING_ACTIVITY,
            "remainingDuration": "not-a-number",
        }

        remaining = cooking_activity_from_push(payload).remaining_seconds
        assert remaining is None or isinstance(remaining, int)

    def test_cooking_activity_from_push_epoch_seconds(self) -> None:
        """Epoch timestamps arrive in millis or seconds; both decode."""
        millis = cooking_activity_from_push(
            {**COOKIDOO_TEST_PUSH_COOKING_ACTIVITY, "completedDate": "1787924895000"}
        )
        seconds = cooking_activity_from_push(
            {**COOKIDOO_TEST_PUSH_COOKING_ACTIVITY, "completedDate": 1787924895}
        )

        assert millis.completed_at is not None
        assert seconds.completed_at is not None
        assert millis.completed_at == seconds.completed_at

    def test_cooking_activity_from_push(self) -> None:
        """Test decoding a remote-monitoring push payload."""
        activity = cooking_activity_from_push(COOKIDOO_TEST_PUSH_COOKING_ACTIVITY)
        assert activity.state == CookidooCookState.RUNNING
        assert activity.is_active
        assert activity.recipe_name == "Purè di patate"
        assert activity.step == "5/9"
        assert activity.target_temperature == 95.0
        assert activity.current_temperature is None  # "---" -> None
        assert activity.is_time_estimated is False  # "false" -> False
        assert activity.recipe_type == "VORWERK"
        assert activity.completed_at is not None
        assert activity.stale_at is not None and activity.stale_at.year == 2026

    def test_cooking_activity_from_push_done_is_inactive(self) -> None:
        """A done cook is not active."""
        activity = cooking_activity_from_push(
            {**COOKIDOO_TEST_PUSH_COOKING_ACTIVITY, "state": "done"}
        )
        assert activity.state == CookidooCookState.DONE
        assert not activity.is_active
