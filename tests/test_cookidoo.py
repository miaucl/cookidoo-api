"""Unit tests for cookidoo-api."""

from datetime import datetime
from http import HTTPStatus

from aiohttp import ClientError, ClientSession
from aioresponses import aioresponses
from dotenv import load_dotenv
import pytest

from cookidoo_api.cookidoo import Cookidoo
from cookidoo_api.exceptions import (
    CookidooAuthException,
    CookidooException,
    CookidooParseException,
    CookidooRequestException,
)
from cookidoo_api.helpers import get_localization_options
from cookidoo_api.types import (
    CookidooAdditionalItem,
    CookidooConfig,
    CookidooIngredientItem,
)
from tests.responses import (
    COOKIDOO_TEST_LOGIN_PAGE_HTML,
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
    COOKIDOO_TEST_RESPONSE_REMOVE_CUSTOM_RECIPE_FROM_CALENDAR,
    COOKIDOO_TEST_RESPONSE_REMOVE_RECIPE_FROM_CALENDAR,
    COOKIDOO_TEST_RESPONSE_REMOVE_RECIPE_FROM_CUSTOM_COLLECTION,
    COOKIDOO_TEST_RESPONSE_USER_INFO,
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


class TestLogin:
    """Tests for login method."""

    async def test_login_success(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test successful login via browser OAuth2 flow."""
        import re

        # Mock the login page (GET follows redirects to CIAM login page)
        mocked.get(
            re.compile(r"https://cookidoo\.ch/profile/de-CH/login.*"),
            status=HTTPStatus.OK,
            body=COOKIDOO_TEST_LOGIN_PAGE_HTML,
        )

        # Mock the CIAM login POST (returns redirect with auth cookies)
        mocked.post(
            "https://ciam.prod.cookidoo.vorwerk-digital.com/login-srv/login",
            status=HTTPStatus.OK,
        )

        # Manually set cookies since aioresponses doesn't handle Set-Cookie
        cookidoo._session.cookie_jar.update_cookies(
            {"_oauth2_proxy": "test-proxy-value", "v-authenticated": "test-auth-value"}
        )

        await cookidoo.login()
        assert cookidoo._logged_in

    async def test_login_page_unreachable(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test login when login page returns error."""
        import re

        mocked.get(
            re.compile(r"https://cookidoo\.ch/profile/de-CH/login.*"),
            status=HTTPStatus.SERVICE_UNAVAILABLE,
        )

        with pytest.raises(CookidooAuthException, match="could not reach login page"):
            await cookidoo.login()

    async def test_login_page_parse_error(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test login when requestId cannot be extracted."""
        import re

        mocked.get(
            re.compile(r"https://cookidoo\.ch/profile/de-CH/login.*"),
            status=HTTPStatus.OK,
            body="<html><body>No form here</body></html>",
        )

        with pytest.raises(CookidooParseException, match="could not extract requestId"):
            await cookidoo.login()

    async def test_login_invalid_credentials(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test login with invalid credentials (no auth cookies set)."""
        import re

        mocked.get(
            re.compile(r"https://cookidoo\.ch/profile/de-CH/login.*"),
            status=HTTPStatus.OK,
            body=COOKIDOO_TEST_LOGIN_PAGE_HTML,
        )
        mocked.post(
            "https://ciam.prod.cookidoo.vorwerk-digital.com/login-srv/login",
            status=HTTPStatus.OK,
        )

        with pytest.raises(
            CookidooAuthException, match="authentication cookies were not set"
        ):
            await cookidoo.login()

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
        """Test exceptions."""
        import re

        mocked.get(
            re.compile(r"https://cookidoo\.ch/profile/de-CH/login.*"),
            exception=exception,
        )
        with pytest.raises(CookidooRequestException):
            await cookidoo.login()


class TestCookiePersistence:
    """Tests for cookie save/load methods."""

    async def test_save_and_load_cookies(
        self, cookidoo: Cookidoo, tmp_path: object
    ) -> None:
        """Test saving and loading cookies."""
        import pathlib

        cookie_file = pathlib.Path(str(tmp_path)) / "cookies.json"

        # Set some cookies on the session
        cookidoo._session.cookie_jar.update_cookies(
            {"_oauth2_proxy": "proxy-val", "v-authenticated": "auth-val"}
        )

        # Save
        cookidoo.save_cookies(cookie_file)
        assert cookie_file.exists()

        # Load into a fresh Cookidoo instance on same session
        # (clear cookies first)
        cookidoo._session.cookie_jar.clear()
        assert not cookidoo._logged_in or True  # reset
        cookidoo._logged_in = False

        cookidoo.load_cookies(cookie_file)
        assert cookidoo._logged_in

        cookie_names = {c.key for c in cookidoo._session.cookie_jar}
        assert "_oauth2_proxy" in cookie_names
        assert "v-authenticated" in cookie_names

    async def test_load_cookies_missing_file(self, cookidoo: Cookidoo) -> None:
        """Test loading cookies from nonexistent file."""
        from cookidoo_api.exceptions import CookidooConfigException

        with pytest.raises(CookidooConfigException, match="Cannot load cookies"):
            cookidoo.load_cookies("/nonexistent/path/cookies.json")

    async def test_load_cookies_without_auth_cookies(
        self, cookidoo: Cookidoo, tmp_path: object
    ) -> None:
        """Test that loading cookies without required auth cookies does not set logged_in."""
        import json
        import pathlib

        cookie_file = pathlib.Path(str(tmp_path)) / "cookies.json"
        cookie_file.write_text(
            json.dumps(
                [{"key": "some_other", "value": "val", "domain": "", "path": "/"}]
            )
        )
        cookidoo._logged_in = False
        cookidoo.load_cookies(cookie_file)
        assert not cookidoo._logged_in

    async def test_corrupted_cookies_recovery(
        self, mocked: aioresponses, cookidoo: Cookidoo, tmp_path: object
    ) -> None:
        """Test recovery flow: load expired/corrupted cookies, API fails, re-login succeeds."""
        import pathlib
        import re

        cookie_file = pathlib.Path(str(tmp_path)) / "cookies.json"

        # Set corrupted/expired auth cookies
        cookidoo._session.cookie_jar.update_cookies(
            {"_oauth2_proxy": "corrupted-value", "v-authenticated": "expired"}
        )
        cookidoo.save_cookies(cookie_file)

        # Clear and reload the corrupted cookies
        cookidoo._session.cookie_jar.clear()
        cookidoo._logged_in = False
        cookidoo.load_cookies(cookie_file)
        assert cookidoo._logged_in  # Cookies are present, so flag is set

        # API call fails with 401 because cookies are invalid
        mocked.get(
            "https://cookidoo.ch/community/profile",
            status=HTTPStatus.UNAUTHORIZED,
            payload={"error": "Unauthorized", "error_description": "Token expired"},
        )
        with pytest.raises(CookidooAuthException):
            await cookidoo.get_user_info()

        # Recovery: re-login
        mocked.get(
            re.compile(r"https://cookidoo\.ch/profile/de-CH/login.*"),
            status=HTTPStatus.OK,
            body=COOKIDOO_TEST_LOGIN_PAGE_HTML,
        )
        mocked.post(
            "https://ciam.prod.cookidoo.vorwerk-digital.com/login-srv/login",
            status=HTTPStatus.OK,
        )
        cookidoo._session.cookie_jar.update_cookies(
            {
                "_oauth2_proxy": "fresh-proxy-value",
                "v-authenticated": "fresh-auth-value",
            }
        )
        await cookidoo.login()
        assert cookidoo._logged_in

        # API call now succeeds
        mocked.get(
            "https://cookidoo.ch/community/profile",
            payload=COOKIDOO_TEST_RESPONSE_USER_INFO,
            status=HTTPStatus.OK,
        )
        data = await cookidoo.get_user_info()
        assert data.username == COOKIDOO_TEST_RESPONSE_USER_INFO["userInfo"]["username"]  # type: ignore[index]

        # Save fresh cookies for next run
        cookidoo.save_cookies(cookie_file)


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
