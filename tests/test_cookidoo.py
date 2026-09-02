"""Unit tests for cookidoo-api."""

from collections.abc import Callable
from datetime import datetime
from http import HTTPStatus
import pathlib
import re
from typing import Any, cast

from aiohttp import ClientError, ClientSession
from aioresponses import CallbackResult, aioresponses
from dotenv import load_dotenv
import pytest
from yarl import URL

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
from cookidoo_api.raw_types import CustomRecipeJSON, CustomRecipesJSON
from cookidoo_api.types import (
    CookidooAdditionalItem,
    CookidooAuthData,
    CookidooConfig,
    CookidooCreateCustomRecipe,
    CookidooCustomAnnotation,
    CookidooIngredientAnnotation,
    CookidooIngredientItem,
    CookidooInstruction,
    CookidooModeAnnotation,
    CookidooSearchResult,
    CookidooStepSettings,
    CookidooTemperatureSetting,
    CookidooTTSAnnotation,
    CookidooUpdateCustomRecipe,
    ThermomixBrowningPower,
    ThermomixDirection,
    ThermomixMachineType,
    ThermomixMode,
    ThermomixSpeed,
    ThermomixSteamingAccessory,
    ThermomixTemperature,
)
from tests.conftest import TEST_CLIENT_ID, TEST_REDIRECT_URI
from tests.responses import (
    COOKIDOO_TEST_LOGIN_PAGE_HTML,
    COOKIDOO_TEST_OIDC_DISCOVERY,
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
    COOKIDOO_TEST_RESPONSE_CREATE_CUSTOM_RECIPE_STUB,
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
    COOKIDOO_TEST_RESPONSE_REMOVE_CUSTOM_RECIPE_FROM_CALENDAR,
    COOKIDOO_TEST_RESPONSE_REMOVE_RECIPE_FROM_CALENDAR,
    COOKIDOO_TEST_RESPONSE_REMOVE_RECIPE_FROM_CUSTOM_COLLECTION,
    COOKIDOO_TEST_RESPONSE_SEARCH_RECIPES,
    COOKIDOO_TEST_RESPONSE_UPDATE_CUSTOM_RECIPE,
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
            "https://cookidoo.ch/community/profile",
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
            "https://cookidoo.ch/community/profile",
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
            "https://cookidoo.ch/community/profile",
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
            "https://cookidoo.ch/community/profile",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.get_user_info()

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.get(
            "https://cookidoo.ch/community/profile",
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
            "https://cookidoo.ch/community/profile",
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
            "https://cookidoo.ch/community/profile",
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
            "https://cookidoo.ch/community/profile",
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

    async def test_search_recipes_without_query_unexpected_status(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test an unexpected HTTP status."""
        mocked.get(
            "https://cookidoo.ch/search/de",
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.search_recipes()

    async def test_search_recipes_non_mapping_response(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test a valid JSON response with an unexpected shape."""
        mocked.get(
            "https://cookidoo.ch/search/de",
            payload=[],
            status=HTTPStatus.OK,
        )

        with pytest.raises(CookidooParseException):
            await cookidoo.search_recipes()


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


# ======================================================================
# Tests for create_custom_recipe
# ======================================================================

CREATE_URL = "https://cookidoo.ch/created-recipes/de-CH"
UPDATE_URL = "https://cookidoo.ch/created-recipes/de-CH/01K2CTJ9Y1BABRG5MXK44CFZS4"


def _mock_create_and_update(mocked: aioresponses) -> None:
    """Register both POST (stub) and PATCH (full) mock responses."""
    mocked.post(
        CREATE_URL,
        payload=COOKIDOO_TEST_RESPONSE_CREATE_CUSTOM_RECIPE_STUB,
        status=HTTPStatus.OK,
    )
    mocked.patch(
        UPDATE_URL,
        payload=COOKIDOO_TEST_RESPONSE_UPDATE_CUSTOM_RECIPE,
        status=HTTPStatus.OK,
    )
    mocked.get(
        UPDATE_URL,
        payload=cast(CustomRecipesJSON, COOKIDOO_TEST_RESPONSE_LIST_CUSTOM_RECIPES)[
            "items"
        ][0],
        status=HTTPStatus.OK,
    )


class TestCreateCustomRecipe:
    """Tests for create_custom_recipe method."""

    async def test_create_custom_recipe(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for create_custom_recipe with simple string steps."""
        _mock_create_and_update(mocked)

        created_recipe = await cookidoo.create_custom_recipe(
            CookidooCreateCustomRecipe(
                name="Test Recipe",
                ingredients=["200g flour", "2 eggs"],
                instructions=["Mix ingredients", "Bake at 180C"],
                serving_size=4,
                active_time=1800,
                total_time=3600,
            )
        )

        assert created_recipe.id == "01K2CTJ9Y1BABRG5MXK44CFZS4"
        requests = [call for calls in mocked.requests.values() for call in calls]
        create_request, update_request = requests[:2]
        assert create_request.kwargs["json"] == {"recipeName": "Test Recipe"}
        assert update_request.kwargs["json"] == {
            "name": "Test Recipe",
            "image": None,
            "isImageOwnedByUser": False,
            "tools": ["TM7"],
            "yield": {"value": 4, "unitText": "portion"},
            "prepTime": 1800,
            "cookTime": 1800,
            "totalTime": 3600,
            "ingredients": [
                {"type": "INGREDIENT", "text": "200g flour"},
                {"type": "INGREDIENT", "text": "2 eggs"},
            ],
            "instructions": [
                {"type": "STEP", "text": "Mix ingredients"},
                {"type": "STEP", "text": "Bake at 180C"},
            ],
            "hints": "",
            "workStatus": "PRIVATE",
            "recipeMetadata": {"requiresAnnotationsCheck": False},
        }

    async def test_create_custom_recipe_with_annotations(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Preserve the legacy multi-annotation payload using public models."""
        _mock_create_and_update(mocked)

        created_recipe = await cookidoo.create_custom_recipe(
            CookidooCreateCustomRecipe(
                name="Test Recipe",
                ingredients=["200g flour", "2 eggs"],
                instructions=[
                    CookidooInstruction(
                        text="Add 200g flour and mix 1 min/speed 3",
                        annotations=[
                            CookidooIngredientAnnotation(
                                slot="200g flour", description="200g flour"
                            ),
                            CookidooTTSAnnotation(
                                slot="1 min/speed 3", time=60, speed="3"
                            ),
                        ],
                    )
                ],
                serving_size=4,
                active_time=1800,
                total_time=3600,
            )
        )
        assert created_recipe.id == "01K2CTJ9Y1BABRG5MXK44CFZS4"

    async def test_create_custom_recipe_default_machine_type(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test that default machine type is TM7 when none provided."""
        _mock_create_and_update(mocked)

        created_recipe = await cookidoo.create_custom_recipe(
            CookidooCreateCustomRecipe(
                name="Test Recipe",
                ingredients=["salt"],
                instructions=["Cook it"],
                serving_size=4,
                active_time=1800,
                total_time=3600,
            )
        )
        assert created_recipe.id == "01K2CTJ9Y1BABRG5MXK44CFZS4"

    async def test_create_custom_recipe_with_enum_machine_types(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test create_custom_recipe with ThermomixMachineType enum values."""
        _mock_create_and_update(mocked)

        created_recipe = await cookidoo.create_custom_recipe(
            CookidooCreateCustomRecipe(
                name="Test Recipe",
                ingredients=["water"],
                instructions=["Boil"],
                serving_size=4,
                active_time=1800,
                total_time=3600,
                tools=[ThermomixMachineType.TM6, ThermomixMachineType.TM7],
            )
        )
        assert created_recipe.id == "01K2CTJ9Y1BABRG5MXK44CFZS4"

    async def test_create_custom_recipe_missing_recipe_id(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test create_custom_recipe raises when recipeId is missing."""
        mocked.post(
            CREATE_URL,
            payload={"status": "ACTIVE"},
            status=HTTPStatus.OK,
        )

        with pytest.raises(CookidooParseException, match="No recipe ID returned"):
            await cookidoo.create_custom_recipe(
                CookidooCreateCustomRecipe(
                    name="Test Recipe",
                    ingredients=["flour"],
                    instructions=["Mix"],
                    serving_size=4,
                    active_time=30,
                    total_time=60,
                )
            )

    @pytest.mark.parametrize(
        "exception",
        [
            TimeoutError,
            ClientError,
        ],
    )
    async def test_create_custom_recipe_request_exception(
        self,
        mocked: aioresponses,
        cookidoo: Cookidoo,
        exception: Exception,
    ) -> None:
        """Test create_custom_recipe request exception."""
        mocked.post(
            CREATE_URL,
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.create_custom_recipe(
                CookidooCreateCustomRecipe(
                    name="Test Recipe",
                    ingredients=["flour"],
                    instructions=["Mix"],
                    serving_size=4,
                    active_time=30,
                    total_time=60,
                )
            )

    async def test_create_custom_recipe_unauthorized(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test create_custom_recipe unauthorized exception."""
        mocked.post(
            CREATE_URL,
            status=HTTPStatus.UNAUTHORIZED,
            payload={"error_description": ""},
        )

        with pytest.raises(CookidooAuthException):
            await cookidoo.create_custom_recipe(
                CookidooCreateCustomRecipe(
                    name="Test Recipe",
                    ingredients=["flour"],
                    instructions=["Bake"],
                    serving_size=4,
                    active_time=30,
                    total_time=60,
                )
            )

    async def test_create_custom_recipe_patch_exception(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Propagate request failures while populating the created stub."""
        mocked.post(
            CREATE_URL,
            payload=COOKIDOO_TEST_RESPONSE_CREATE_CUSTOM_RECIPE_STUB,
            status=HTTPStatus.OK,
        )
        mocked.patch(UPDATE_URL, exception=ClientError())

        with pytest.raises(CookidooRequestException) as exc_info:
            await cookidoo.create_custom_recipe(
                CookidooCreateCustomRecipe(
                    name="Test Recipe",
                    ingredients=["flour"],
                    instructions=["Mix"],
                    serving_size=4,
                    active_time=30,
                    total_time=60,
                )
            )

        assert any(
            "Orphaned custom recipe stub id: 01K2CTJ9Y1BABRG5MXK44CFZS4" in note
            for note in exc_info.value.__notes__
        )

    async def test_create_custom_recipe_reload_exception(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Propagate failures while loading the completed recipe."""
        mocked.post(
            CREATE_URL,
            payload=COOKIDOO_TEST_RESPONSE_CREATE_CUSTOM_RECIPE_STUB,
            status=HTTPStatus.OK,
        )
        mocked.patch(UPDATE_URL, status=HTTPStatus.NO_CONTENT)
        mocked.get(UPDATE_URL, exception=TimeoutError())

        with pytest.raises(CookidooRequestException) as exc_info:
            await cookidoo.create_custom_recipe(
                CookidooCreateCustomRecipe(
                    name="Test Recipe",
                    ingredients=["flour"],
                    instructions=["Mix"],
                    serving_size=4,
                    active_time=30,
                    total_time=60,
                )
            )

        assert any(
            "Orphaned custom recipe stub id: 01K2CTJ9Y1BABRG5MXK44CFZS4" in note
            for note in exc_info.value.__notes__
        )

    async def test_create_custom_recipe_from_model(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Create from the public model and return the complete recipe."""
        _mock_create_and_update(mocked)
        mocked.get(
            UPDATE_URL,
            payload=cast(CustomRecipesJSON, COOKIDOO_TEST_RESPONSE_LIST_CUSTOM_RECIPES)[
                "items"
            ][0],
            status=HTTPStatus.OK,
        )
        recipe = CookidooCreateCustomRecipe(
            name="Test Recipe",
            ingredients=["200g flour"],
            instructions=[
                CookidooInstruction(
                    "Cook",
                    CookidooStepSettings(time=60, temperature=100, speed=2.5),
                )
            ],
            serving_size=2,
            active_time=600,
            total_time=1800,
            tools=[ThermomixMachineType.TM6],
            image="prod/img/customer-recipe/smoke-test-recipe.jpg",
        )

        result = await cookidoo.create_custom_recipe(recipe)

        assert result.id == "01K2CTJ9Y1BABRG5MXK44CFZS4"
        update_request = next(
            calls[0]
            for (method, _url), calls in mocked.requests.items()
            if str(method).upper() == "PATCH"
        )
        assert update_request.kwargs["json"]["instructions"] == [
            {
                "type": "STEP",
                "text": "Cook",
                "time": 60,
                "temperature": 100,
                "speed": 2.5,
            }
        ]
        assert update_request.kwargs["json"]["cookTime"] == 1200
        assert (
            update_request.kwargs["json"]["image"]
            == "prod/img/customer-recipe/smoke-test-recipe.jpg"
        )
        assert update_request.kwargs["json"]["isImageOwnedByUser"] is True

    async def test_create_custom_recipe_validates_before_request(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Reject invalid input without leaving a blank remote recipe."""
        recipe = CookidooCreateCustomRecipe(
            name="Invalid",
            ingredients=[],
            instructions=[],
            serving_size=0,
            active_time=60,
            total_time=30,
        )

        with pytest.raises(ValueError, match="servings"):
            await cookidoo.create_custom_recipe(recipe)

        assert mocked.requests == {}

    async def test_create_custom_recipe_rejects_invalid_image(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Reject CDN/display image URLs before creating a stub."""
        recipe = CookidooCreateCustomRecipe(
            name="Invalid image",
            ingredients=["flour"],
            instructions=["Mix"],
            serving_size=2,
            active_time=60,
            total_time=120,
            image="https://assets.tmecosys.com/image/upload/recipe.jpg",
        )

        with pytest.raises(ValueError, match="customer-recipe"):
            await cookidoo.create_custom_recipe(recipe)

        assert mocked.requests == {}


class TestUpdateCustomRecipe:
    """Tests for partial custom recipe updates."""

    async def test_update_custom_recipe(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Merge omitted fields, patch once, and reload the recipe."""
        url = "https://cookidoo.ch/created-recipes/de-CH/01K2CVHD1DXG1PVETNVV3JPKWW"
        mocked.get(
            url,
            payload=COOKIDOO_TEST_RESPONSE_GET_CUSTOM_RECIPE,
            status=HTTPStatus.OK,
            repeat=True,
        )
        mocked.patch(url, status=HTTPStatus.NO_CONTENT)

        result = await cookidoo.update_custom_recipe(
            "01K2CVHD1DXG1PVETNVV3JPKWW",
            CookidooUpdateCustomRecipe(
                name="Updated recipe",
                instructions=[
                    CookidooInstruction(
                        "Heat",
                        CookidooStepSettings(time=120, temperature="varoma", speed="2"),
                    )
                ],
            ),
        )

        assert result.id == "01K2CVHD1DXG1PVETNVV3JPKWW"
        update_request = next(
            calls[0]
            for (method, _url), calls in mocked.requests.items()
            if str(method).upper() == "PATCH"
        )
        payload = update_request.kwargs["json"]
        assert payload["name"] == "Updated recipe"
        assert payload["ingredients"] == [
            {"type": "INGREDIENT", "text": ingredient}
            for ingredient in cast(
                list[str],
                cast(CustomRecipeJSON, COOKIDOO_TEST_RESPONSE_GET_CUSTOM_RECIPE)[
                    "recipeContent"
                ]["recipeIngredient"],
            )
        ]
        assert payload["instructions"] == [
            {
                "type": "STEP",
                "text": "Heat",
                "time": 120,
                "temperature": "varoma",
                "speed": "2",
            }
        ]
        assert payload["prepTime"] == 600
        assert payload["cookTime"] == 1200
        assert payload["totalTime"] == 1800

    async def test_edit_preserves_structured_recipe_fields(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Keep structured instructions and metadata when editing one field."""
        url = "https://cookidoo.ch/created-recipes/de-CH/structured-recipe"
        response: CustomRecipeJSON = {
            "recipeId": "structured-recipe",
            "workStatus": "PUBLIC",
            "recipeContent": {
                "name": "Original",
                "prepTime": 60,
                "totalTime": 180,
                "tools": ["TM6"],
                "yield": {"value": 2, "unitText": "serving"},
                "ingredients": [{"type": "INGREDIENT", "text": "water"}],
                "instructions": [
                    {
                        "type": "STEP",
                        "text": "Heat water",
                        "time": 120,
                        "temperature": 100,
                        "speed": "2",
                        "annotations": [
                            {
                                "type": "INGREDIENT",
                                "data": {"description": "water"},
                                "position": {"offset": 5, "length": 5},
                            },
                            {
                                "type": "FUTURE_MODE",
                                "name": "future",
                                "data": {"unknown": {"enabled": True}},
                                "position": {"offset": 0, "length": 4},
                            },
                        ],
                    }
                ],
                "hints": "first\nsecond",
                "isImageOwnedByUser": True,
                "recipeMetadata": {"requiresAnnotationsCheck": True},
            },
        }
        mocked.get(url, payload=response, status=HTTPStatus.OK, repeat=True)
        mocked.patch(url, status=HTTPStatus.NO_CONTENT)

        await cookidoo.update_custom_recipe(
            "structured-recipe", CookidooUpdateCustomRecipe(name="Updated")
        )

        update_request = next(
            calls[0]
            for (method, _url), calls in mocked.requests.items()
            if str(method).upper() == "PATCH"
        )
        payload = update_request.kwargs["json"]
        assert payload["instructions"] == response["recipeContent"]["instructions"]
        assert payload["hints"] == "first\nsecond"
        assert payload["yield"] == {"value": 2, "unitText": "serving"}
        assert payload["workStatus"] == "PUBLIC"
        assert payload["image"] is None
        assert payload["isImageOwnedByUser"] is False
        assert payload["recipeMetadata"] == {"requiresAnnotationsCheck": True}

    async def test_update_drops_display_image_urls(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Do not echo CDN/display image URLs back to the update endpoint."""
        url = "https://cookidoo.ch/created-recipes/de-CH/01K2CVHD1DXG1PVETNVV3JPKWW"
        mocked.get(
            url,
            payload=COOKIDOO_TEST_RESPONSE_GET_CUSTOM_RECIPE,
            status=HTTPStatus.OK,
            repeat=True,
        )
        mocked.patch(url, status=HTTPStatus.NO_CONTENT)

        await cookidoo.update_custom_recipe(
            "01K2CVHD1DXG1PVETNVV3JPKWW",
            CookidooUpdateCustomRecipe(name="Updated without image echo"),
        )

        update_request = next(
            calls[0]
            for (method, _url), calls in mocked.requests.items()
            if str(method).upper() == "PATCH"
        )
        payload = update_request.kwargs["json"]
        assert payload["name"] == "Updated without image echo"
        assert payload["image"] is None
        assert payload["isImageOwnedByUser"] is False

    async def test_update_keeps_valid_customer_recipe_image(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Preserve customer-recipe image paths accepted by Cookidoo."""
        url = "https://cookidoo.ch/created-recipes/de-CH/image-recipe"
        response: CustomRecipeJSON = {
            "recipeId": "image-recipe",
            "workStatus": "PRIVATE",
            "recipeContent": {
                "name": "Original",
                "prepTime": 60,
                "totalTime": 180,
                "tools": ["TM7"],
                "yield": {"value": 2, "unitText": "portion"},
                "ingredients": [],
                "instructions": [],
                "image": "prod/img/customer-recipe/my-photo.jpg",
                "isImageOwnedByUser": True,
            },
        }
        mocked.get(url, payload=response, status=HTTPStatus.OK, repeat=True)
        mocked.patch(url, status=HTTPStatus.NO_CONTENT)

        await cookidoo.update_custom_recipe(
            "image-recipe", CookidooUpdateCustomRecipe(name="Updated")
        )

        update_request = next(
            calls[0]
            for (method, _url), calls in mocked.requests.items()
            if str(method).upper() == "PATCH"
        )
        payload = update_request.kwargs["json"]
        assert payload["image"] == "prod/img/customer-recipe/my-photo.jpg"
        assert payload["isImageOwnedByUser"] is True

    async def test_update_custom_recipe_rejects_invalid_image(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Reject CDN/display image URLs before fetching the existing recipe."""
        with pytest.raises(ValueError, match="customer-recipe"):
            await cookidoo.update_custom_recipe(
                "01K2CVHD1DXG1PVETNVV3JPKWW",
                CookidooUpdateCustomRecipe(
                    image="https://assets.tmecosys.com/image/upload/recipe.jpg",
                    image_owned_by_user=True,
                ),
            )

        assert mocked.requests == {}

    async def test_update_custom_recipe_image_ownership_defaults(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Default ownership to True when a caller supplies a new image."""
        url = "https://cookidoo.ch/created-recipes/de-CH/01K2CVHD1DXG1PVETNVV3JPKWW"
        mocked.get(
            url,
            payload=COOKIDOO_TEST_RESPONSE_GET_CUSTOM_RECIPE,
            status=HTTPStatus.OK,
            repeat=True,
        )
        mocked.patch(url, status=HTTPStatus.NO_CONTENT)

        await cookidoo.update_custom_recipe(
            "01K2CVHD1DXG1PVETNVV3JPKWW",
            CookidooUpdateCustomRecipe(
                image="prod/img/customer-recipe/new-photo.jpg",
            ),
        )

        update_request = next(
            calls[0]
            for (method, _url), calls in mocked.requests.items()
            if str(method).upper() == "PATCH"
        )
        payload = update_request.kwargs["json"]
        assert payload["image"] == "prod/img/customer-recipe/new-photo.jpg"
        assert payload["isImageOwnedByUser"] is True

    async def test_update_custom_recipe_explicit_image_ownership(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Honor an explicit image_owned_by_user value from the caller."""
        url = "https://cookidoo.ch/created-recipes/de-CH/01K2CVHD1DXG1PVETNVV3JPKWW"
        mocked.get(
            url,
            payload=COOKIDOO_TEST_RESPONSE_GET_CUSTOM_RECIPE,
            status=HTTPStatus.OK,
            repeat=True,
        )
        mocked.patch(url, status=HTTPStatus.NO_CONTENT)

        await cookidoo.update_custom_recipe(
            "01K2CVHD1DXG1PVETNVV3JPKWW",
            CookidooUpdateCustomRecipe(
                image="prod/img/customer-recipe/shared-photo.jpg",
                image_owned_by_user=False,
            ),
        )

        update_request = next(
            calls[0]
            for (method, _url), calls in mocked.requests.items()
            if str(method).upper() == "PATCH"
        )
        payload = update_request.kwargs["json"]
        assert payload["image"] == "prod/img/customer-recipe/shared-photo.jpg"
        assert payload["isImageOwnedByUser"] is False

    async def test_update_custom_recipe_unauthorized(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Propagate authorization failures from the PATCH request."""
        url = "https://cookidoo.ch/created-recipes/de-CH/01K2CVHD1DXG1PVETNVV3JPKWW"
        mocked.get(
            url,
            payload=COOKIDOO_TEST_RESPONSE_GET_CUSTOM_RECIPE,
            status=HTTPStatus.OK,
        )
        mocked.patch(
            url,
            status=HTTPStatus.UNAUTHORIZED,
            payload={"error_description": "expired"},
        )

        with pytest.raises(CookidooAuthException):
            await cookidoo.update_custom_recipe(
                "01K2CVHD1DXG1PVETNVV3JPKWW",
                CookidooUpdateCustomRecipe(name="Updated"),
            )


# ======================================================================
# Tests for _process_recipe_steps
# ======================================================================


class TestProcessRecipeSteps:
    """Tests for _process_recipe_steps helper."""

    def test_plain_string_step(self) -> None:
        """Test that a plain string step is converted correctly."""
        steps = ["Mix well"]
        result = Cookidoo._process_recipe_steps(steps, ingredients=[])

        assert len(result) == 1
        assert result[0]["type"] == "STEP"
        assert result[0]["text"] == "Mix well"
        assert "annotations" not in result[0]

    def test_structured_step_without_annotations(self) -> None:
        """Test a structured step without annotations."""
        steps = [CookidooInstruction("Mix well")]

        result = Cookidoo._process_recipe_steps(steps, ingredients=[])

        assert result == [{"type": "STEP", "text": "Mix well"}]

    def test_tts_annotation(self) -> None:
        """Test TTS annotation with offset and length calculation."""
        steps = [
            CookidooInstruction(
                "Mix 2 min/speed 4",
                annotations=[
                    CookidooTTSAnnotation("2 min/speed 4", time=120, speed="4")
                ],
            )
        ]
        result = Cookidoo._process_recipe_steps(steps, ingredients=["flour"])

        assert len(result) == 1
        ann = result[0]["annotations"][0]
        assert ann["type"] == "TTS"
        assert ann["data"] == {"time": 120, "speed": "4"}
        assert ann["position"]["offset"] == 4  # "Mix " = 4 chars
        assert ann["position"]["length"] == 13  # "2 min/speed 4"

    def test_ingredient_annotation_valid(self) -> None:
        """Test valid INGREDIENT annotation passes validation."""
        steps = [
            CookidooInstruction(
                "Add 200g flour and mix",
                annotations=[CookidooIngredientAnnotation("200g flour", "200g flour")],
            )
        ]
        result = Cookidoo._process_recipe_steps(
            steps, ingredients=["200g flour", "2 eggs"]
        )

        assert len(result) == 1
        ann = result[0]["annotations"][0]
        assert ann["type"] == "INGREDIENT"
        assert ann["position"]["offset"] == 4  # "Add "

    def test_ingredient_annotation_invalid(self) -> None:
        """Test INGREDIENT annotation with missing ingredient raises ValueError."""
        steps = [
            CookidooInstruction(
                "Add 200g flour and mix",
                annotations=[CookidooIngredientAnnotation("200g flour", "200g flour")],
            )
        ]
        with pytest.raises(
            ValueError, match="not found in the recipe's ingredient list"
        ):
            Cookidoo._process_recipe_steps(steps, ingredients=["sugar", "butter"])

    def test_slot_not_found_in_text(self) -> None:
        """Test that a missing slot in step text raises ValueError."""
        steps = [
            CookidooInstruction(
                "Mix well",
                annotations=[CookidooTTSAnnotation("nonexistent slot", time=60)],
            )
        ]
        with pytest.raises(ValueError, match="not found in step text"):
            Cookidoo._process_recipe_steps(steps, ingredients=[])

    def test_varoma_temperature_removes_unit(self) -> None:
        """Test that varoma temperature has its unit removed."""
        steps = [
            CookidooInstruction(
                "Cook Varoma/speed 1",
                annotations=[
                    CookidooTTSAnnotation(
                        "Varoma/speed 1",
                        time=300,
                        speed="1",
                        temperature=CookidooTemperatureSetting("varoma"),
                    )
                ],
            )
        ]
        result = Cookidoo._process_recipe_steps(steps, ingredients=[])

        temp = cast(
            dict[str, object], result[0]["annotations"][0]["data"]["temperature"]
        )
        assert "unit" not in temp
        assert temp["value"] == "varoma"

    def test_varoma_temperature_normalizes_value_case(self) -> None:
        """Test that a mixed-case Varoma value is normalized for the API."""
        steps = [
            CookidooInstruction(
                "Cook Varoma/speed 1",
                annotations=[
                    CookidooTTSAnnotation(
                        "Varoma/speed 1",
                        time=300,
                        speed="1",
                        temperature=CookidooTemperatureSetting("Varoma"),
                    )
                ],
            )
        ]

        result = Cookidoo._process_recipe_steps(steps, ingredients=[])

        assert result[0]["annotations"][0]["data"]["temperature"] == {"value": "varoma"}

    def test_normal_temperature_keeps_unit(self) -> None:
        """Test that a normal temperature keeps its unit intact."""
        steps = [
            CookidooInstruction(
                "Heat 100C/speed 2",
                annotations=[
                    CookidooTTSAnnotation(
                        "100C/speed 2",
                        time=300,
                        speed="2",
                        temperature=CookidooTemperatureSetting("100"),
                    )
                ],
            )
        ]
        result = Cookidoo._process_recipe_steps(steps, ingredients=[])

        temp = cast(
            dict[str, object], result[0]["annotations"][0]["data"]["temperature"]
        )
        assert temp["unit"] == "C"
        assert temp["value"] == "100"

    def test_mode_annotation_with_name(self) -> None:
        """Test MODE annotation includes the name field."""
        steps = [
            CookidooInstruction(
                "Knead dough 2 min",
                annotations=[
                    CookidooModeAnnotation("dough 2 min", ThermomixMode.DOUGH, time=120)
                ],
            )
        ]
        result = Cookidoo._process_recipe_steps(steps, ingredients=[])

        ann = result[0]["annotations"][0]
        assert ann["type"] == "MODE"
        assert ann["name"] == "dough"
        assert ann["data"] == {"time": 120}

    def test_mode_annotation_full_settings(self) -> None:
        """Serialize every supported MODE setting with enum values."""
        steps = [
            CookidooInstruction(
                "Brown with Varoma",
                annotations=[
                    CookidooModeAnnotation(
                        slot="Brown with Varoma",
                        mode=ThermomixMode.BROWNING,
                        time=300,
                        temperature=CookidooTemperatureSetting(
                            ThermomixTemperature.VAROMA
                        ),
                        speed=ThermomixSpeed.SPEED_1,
                        direction=ThermomixDirection.CCW,
                        power=ThermomixBrowningPower.INTENSE,
                        accessory=ThermomixSteamingAccessory.VAROMA,
                    )
                ],
            )
        ]

        result = Cookidoo._process_recipe_steps(steps, ingredients=[])

        assert result[0]["annotations"][0] == {
            "type": "MODE",
            "name": "browning",
            "data": {
                "time": 300,
                "temperature": {"value": "varoma"},
                "speed": "1",
                "direction": "CCW",
                "power": "Intense",
                "accessory": "Varoma",
            },
            "position": {"offset": 0, "length": 17},
        }

    def test_custom_annotation_preserves_unknown_data(self) -> None:
        """Keep future annotation types and fields unchanged."""
        steps = [
            CookidooInstruction(
                "Use future mode",
                annotations=[
                    CookidooCustomAnnotation(
                        type="FUTURE_MODE",
                        slot="future mode",
                        data={"newField": {"enabled": True}},
                        name="future",
                    )
                ],
            )
        ]

        result = Cookidoo._process_recipe_steps(steps, ingredients=[])

        assert result[0]["annotations"][0] == {
            "type": "FUTURE_MODE",
            "name": "future",
            "data": {"newField": {"enabled": True}},
            "position": {"offset": 4, "length": 11},
        }

    def test_direct_settings_and_annotations_coexist(self) -> None:
        """Serialize direct guided settings and positioned annotations together."""
        steps = [
            CookidooInstruction(
                "Add water and heat",
                settings=CookidooStepSettings(time=120, temperature=100, speed=2),
                annotations=[CookidooIngredientAnnotation("water", "water")],
            )
        ]

        result = Cookidoo._process_recipe_steps(steps, ingredients=["water"])

        assert result[0]["time"] == 120
        assert result[0]["temperature"] == 100
        assert result[0]["speed"] == 2
        assert result[0]["annotations"][0]["position"] == {
            "offset": 4,
            "length": 5,
        }

    def test_repeated_slot_uses_first_occurrence(self) -> None:
        """Preserve the previous first-match behavior for repeated slots."""
        steps = [
            CookidooInstruction(
                "mix, then mix again",
                annotations=[CookidooTTSAnnotation("mix", time=10)],
            )
        ]

        result = Cookidoo._process_recipe_steps(steps, ingredients=[])

        assert result[0]["annotations"][0]["position"] == {
            "offset": 0,
            "length": 3,
        }

    def test_mixed_string_and_dict_steps(self) -> None:
        """Test a mix of plain strings and typed annotated steps."""
        steps: list[str | CookidooInstruction] = [
            "Preheat oven",
            CookidooInstruction(
                "Mix 1 min/speed 5",
                annotations=[
                    CookidooTTSAnnotation("1 min/speed 5", time=60, speed="5")
                ],
            ),
            "Serve warm",
        ]
        result = Cookidoo._process_recipe_steps(steps, ingredients=[])

        assert len(result) == 3
        assert result[0] == {"type": "STEP", "text": "Preheat oven"}
        assert "annotations" in result[1]
        assert result[2] == {"type": "STEP", "text": "Serve warm"}

    def test_empty_annotation_slot_raises(self) -> None:
        """Reject annotations without a slot before calculating offsets."""
        steps = [
            CookidooInstruction(
                "Mix well",
                annotations=[CookidooTTSAnnotation("", time=60)],
            )
        ]

        with pytest.raises(ValueError, match="Annotation slot must not be empty"):
            Cookidoo._process_recipe_steps(steps, ingredients=[])

    def test_negative_tts_annotation_time_raises(self) -> None:
        """Reject negative TTS annotation times."""
        steps = [
            CookidooInstruction(
                "Mix 1 min",
                annotations=[CookidooTTSAnnotation("1 min", time=-1)],
            )
        ]

        with pytest.raises(ValueError, match="Annotation time must not be negative"):
            Cookidoo._process_recipe_steps(steps, ingredients=[])

    def test_negative_mode_annotation_time_raises(self) -> None:
        """Reject negative MODE annotation times."""
        steps = [
            CookidooInstruction(
                "Knead dough",
                annotations=[
                    CookidooModeAnnotation("dough", ThermomixMode.DOUGH, time=-5)
                ],
            )
        ]

        with pytest.raises(ValueError, match="Annotation time must not be negative"):
            Cookidoo._process_recipe_steps(steps, ingredients=[])

    def test_empty_custom_annotation_type_raises(self) -> None:
        """Reject custom annotations without a type."""
        steps = [
            CookidooInstruction(
                "Use future mode",
                annotations=[
                    CookidooCustomAnnotation(
                        type="",
                        slot="future mode",
                        data={"enabled": True},
                    )
                ],
            )
        ]

        with pytest.raises(
            ValueError, match="Custom annotation type must not be empty"
        ):
            Cookidoo._process_recipe_steps(steps, ingredients=[])

    def test_negative_instruction_time_raises(self) -> None:
        """Reject negative direct instruction settings."""
        steps = [CookidooInstruction("Heat", settings=CookidooStepSettings(time=-1))]

        with pytest.raises(ValueError, match="Instruction time must not be negative"):
            Cookidoo._process_recipe_steps(steps, ingredients=[])

    def test_tts_annotation_serializes_direction(self) -> None:
        """Serialize enum-backed TTS direction values."""
        steps = [
            CookidooInstruction(
                "Mix CW",
                annotations=[
                    CookidooTTSAnnotation(
                        "CW",
                        time=30,
                        direction=ThermomixDirection.CW,
                    )
                ],
            )
        ]

        result = Cookidoo._process_recipe_steps(steps, ingredients=[])

        assert result[0]["annotations"][0]["data"]["direction"] == "CW"

    def test_tts_annotation_without_time_omits_field(self) -> None:
        """Omit optional TTS time when it is not provided."""
        steps = [
            CookidooInstruction(
                "Mix slowly",
                annotations=[CookidooTTSAnnotation("slowly", speed="2")],
            )
        ]

        result = Cookidoo._process_recipe_steps(steps, ingredients=[])

        assert result[0]["annotations"][0]["data"] == {"speed": "2"}

    def test_mode_annotation_without_time(self) -> None:
        """Omit optional MODE time when it is not provided."""
        steps = [
            CookidooInstruction(
                "Knead dough",
                annotations=[
                    CookidooModeAnnotation("dough", ThermomixMode.DOUGH),
                ],
            )
        ]

        result = Cookidoo._process_recipe_steps(steps, ingredients=[])

        assert result[0]["annotations"][0]["data"] == {}

    def test_instruction_settings_only_speed(self) -> None:
        """Serialize partial direct instruction settings."""
        steps = [
            CookidooInstruction(
                "Mix",
                settings=CookidooStepSettings(speed=ThermomixSpeed.SPEED_3),
            )
        ]

        result = Cookidoo._process_recipe_steps(steps, ingredients=[])

        assert result[0] == {"type": "STEP", "text": "Mix", "speed": "3"}

    def test_instruction_settings_only_temperature(self) -> None:
        """Serialize direct instruction temperature without speed."""
        steps = [
            CookidooInstruction(
                "Heat",
                settings=CookidooStepSettings(temperature=100),
            )
        ]

        result = Cookidoo._process_recipe_steps(steps, ingredients=[])

        assert result[0] == {"type": "STEP", "text": "Heat", "temperature": 100}

    def test_instruction_settings_use_enum_values(self) -> None:
        """Serialize enum-backed direct instruction settings."""
        steps = [
            CookidooInstruction(
                "Heat",
                settings=CookidooStepSettings(
                    time=30,
                    temperature=ThermomixTemperature.VAROMA,
                    speed=ThermomixSpeed.SPEED_2,
                ),
            )
        ]

        result = Cookidoo._process_recipe_steps(steps, ingredients=[])

        assert result[0]["temperature"] == "varoma"
        assert result[0]["speed"] == "2"


class TestBuildCustomRecipePayload:
    """Tests for custom recipe payload validation."""

    def test_rejects_blank_name(self) -> None:
        """Reject blank recipe names before building the payload."""
        with pytest.raises(ValueError, match="Recipe name must not be empty"):
            Cookidoo._build_custom_recipe_payload(
                name="   ",
                ingredients=[],
                steps=[],
                servings=1,
                active_time=0,
                total_time=0,
                hints=[],
                machine_types=[ThermomixMachineType.TM7],
                unit_text="portion",
                image=None,
                image_owned_by_user=False,
                work_status="PRIVATE",
                requires_annotations_check=False,
            )

    def test_rejects_negative_times(self) -> None:
        """Reject negative prep or total times."""
        with pytest.raises(ValueError, match="Recipe times must not be negative"):
            Cookidoo._build_custom_recipe_payload(
                name="Recipe",
                ingredients=[],
                steps=[],
                servings=1,
                active_time=-1,
                total_time=10,
                hints=[],
                machine_types=[ThermomixMachineType.TM7],
                unit_text="portion",
                image=None,
                image_owned_by_user=False,
                work_status="PRIVATE",
                requires_annotations_check=False,
            )

    def test_rejects_active_time_greater_than_total(self) -> None:
        """Reject payloads where active time exceeds total time."""
        with pytest.raises(ValueError, match="Active time must not exceed total time"):
            Cookidoo._build_custom_recipe_payload(
                name="Recipe",
                ingredients=[],
                steps=[],
                servings=1,
                active_time=120,
                total_time=60,
                hints=[],
                machine_types=[ThermomixMachineType.TM7],
                unit_text="portion",
                image=None,
                image_owned_by_user=False,
                work_status="PRIVATE",
                requires_annotations_check=False,
            )

    def test_rejects_blank_unit_text(self) -> None:
        """Reject blank yield unit text."""
        with pytest.raises(ValueError, match="Recipe unit text must not be empty"):
            Cookidoo._build_custom_recipe_payload(
                name="Recipe",
                ingredients=[],
                steps=[],
                servings=1,
                active_time=0,
                total_time=60,
                hints=[],
                machine_types=[ThermomixMachineType.TM7],
                unit_text=" ",
                image=None,
                image_owned_by_user=False,
                work_status="PRIVATE",
                requires_annotations_check=False,
            )


# ======================================================================
# Tests for Thermomix Enums
# ======================================================================


class TestThermomixEnums:
    """Tests for Thermomix enum types."""

    def test_machine_type_values(self) -> None:
        """Test ThermomixMachineType enum has expected members."""
        assert ThermomixMachineType.TM5.value == "TM5"
        assert ThermomixMachineType.TM6.value == "TM6"
        assert ThermomixMachineType.TM7.value == "TM7"
        assert ThermomixMachineType.TM31.value == "TM31"
        assert len(ThermomixMachineType) == 4

    def test_machine_type_is_str(self) -> None:
        """Test ThermomixMachineType members behave as strings."""
        assert isinstance(ThermomixMachineType.TM7, str)
        assert ThermomixMachineType.TM7 == "TM7"

    def test_speed_values(self) -> None:
        """Test ThermomixSpeed enum has soft and numeric values."""
        assert ThermomixSpeed.SOFT.value == "soft"
        assert ThermomixSpeed.SPEED_1.value == "1"
        assert ThermomixSpeed.SPEED_10.value == "10"
        # str behaviour
        assert isinstance(ThermomixSpeed.SOFT, str)

    def test_direction_values(self) -> None:
        """Test ThermomixDirection enum values."""
        assert ThermomixDirection.CW.value == "CW"
        assert ThermomixDirection.CCW.value == "CCW"
        assert len(ThermomixDirection) == 2

    def test_temperature_values(self) -> None:
        """Test ThermomixTemperature enum includes varoma and numeric values."""
        assert ThermomixTemperature.VAROMA.value == "varoma"
        assert ThermomixTemperature.TEMP_37.value == "37"
        assert ThermomixTemperature.TEMP_120.value == "120"
        assert isinstance(ThermomixTemperature.VAROMA, str)

    def test_mode_values(self) -> None:
        """Test ThermomixMode enum values."""
        assert ThermomixMode.DOUGH.value == "dough"
        assert ThermomixMode.BROWNING.value == "browning"
        assert ThermomixMode.TURBO.value == "turbo"
        assert ThermomixMode.STEAMING.value == "steaming"
        assert ThermomixMode.BLEND.value == "blend"
        assert ThermomixMode.WARM_UP.value == "warm_up"
        assert ThermomixMode.RICE_COOKER.value == "rice_cooker"

    def test_browning_power_values(self) -> None:
        """Test ThermomixBrowningPower enum values."""
        assert ThermomixBrowningPower.GENTLE.value == "Gentle"
        assert ThermomixBrowningPower.INTENSE.value == "Intense"
        assert len(ThermomixBrowningPower) == 2

    def test_steaming_accessory_values(self) -> None:
        """Test ThermomixSteamingAccessory enum values."""
        assert ThermomixSteamingAccessory.VAROMA.value == "Varoma"
        assert ThermomixSteamingAccessory.SIMMERING_BASKET.value == "SimmeringBasket"
        assert (
            ThermomixSteamingAccessory.VAROMA_AND_SIMMERING_BASKET.value
            == "VaromaAndSimmeringBasket"
        )
        assert len(ThermomixSteamingAccessory) == 3
