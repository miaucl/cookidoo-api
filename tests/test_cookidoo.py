"""Unit tests for cookidoo-api."""

from http import HTTPStatus

from aiohttp import ClientError
from aioresponses import aioresponses
from dotenv import load_dotenv
import pytest

from cookidoo_api.const import DEFAULT_COOKIDOO_CONFIG
from cookidoo_api.cookidoo import Cookidoo
from cookidoo_api.exceptions import (
    CookidooAuthException,
    CookidooConfigException,
    CookidooException,
    CookidooParseException,
    CookidooRequestException,
)
from tests.responses import (
    COOKIDOO_TEST_RESPONSE_ACTIVE_SUBSCRIPTION,
    COOKIDOO_TEST_RESPONSE_ADD_ADDITIONAL_ITEMS,
    COOKIDOO_TEST_RESPONSE_ADD_INGREDIENTS_FOR_RECIPES,
    COOKIDOO_TEST_RESPONSE_AUTH_RESPONSE,
    COOKIDOO_TEST_RESPONSE_EDIT_ADDITIONAL_ITEMS,
    COOKIDOO_TEST_RESPONSE_EDIT_ADDITIONAL_ITEMS_OWNERSHIP,
    COOKIDOO_TEST_RESPONSE_EDIT_INGREDIENTS_OWNERSHIP,
    COOKIDOO_TEST_RESPONSE_GET_ADDITIONAL_ITEMS,
    COOKIDOO_TEST_RESPONSE_GET_INGREDIENTS,
    COOKIDOO_TEST_RESPONSE_GET_RECIPE_DETAILS,
    COOKIDOO_TEST_RESPONSE_GET_SHOPPING_LIST_RECIPES,
    COOKIDOO_TEST_RESPONSE_INACTIVE_SUBSCRIPTION,
    COOKIDOO_TEST_RESPONSE_USER_INFO,
)

load_dotenv()


class TestLogin:
    """Tests for login method."""

    async def test_refresh_before_login(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test refresh before login."""
        mocked.post(
            "https://eu.login.vorwerk.com/oauth2/token",
            status=400,
        )
        expected = "No auth data available, please log in first"
        with pytest.raises(CookidooConfigException, match=expected):
            await cookidoo.refresh_token()

    async def test_mail_invalid(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test login with invalid e-mail."""
        mocked.post(
            "https://eu.login.vorwerk.com/oauth2/token",
            status=400,
        )
        expected = "Access token request failed due to bad request, please check your email or refresh token."
        with pytest.raises(CookidooAuthException, match=expected):
            await cookidoo.login()

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test login with unauthorized user."""
        mocked.post(
            "https://eu.login.vorwerk.com/oauth2/token",
            status=HTTPStatus.UNAUTHORIZED,
            payload={"error_description": ""},
        )
        expected = "Access token request failed due to authorization failure, please check your email and password or refresh token."
        with pytest.raises(CookidooAuthException, match=expected):
            await cookidoo.login()

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
            "https://eu.login.vorwerk.com/oauth2/token",
            status=status,
            body="not json",
            content_type="application/json",
        )

        with pytest.raises(exception):
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
        mocked.post("https://eu.login.vorwerk.com/oauth2/token", exception=exception)
        with pytest.raises(CookidooRequestException):
            await cookidoo.login()

    async def test_login_and_refresh(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test login and refresh with valid user."""

        mocked.post(
            "https://eu.login.vorwerk.com/oauth2/token",
            status=HTTPStatus.OK,
            payload=COOKIDOO_TEST_RESPONSE_AUTH_RESPONSE,
        )

        assert cookidoo.auth_data is None
        data = await cookidoo.login()
        for key, value in data.items():
            assert value == COOKIDOO_TEST_RESPONSE_AUTH_RESPONSE[key]
        assert cookidoo.expires_in > 0
        assert cookidoo.localization == DEFAULT_COOKIDOO_CONFIG["localization"]

        mocked.post(
            "https://eu.login.vorwerk.com/oauth2/token",
            status=HTTPStatus.OK,
            payload=COOKIDOO_TEST_RESPONSE_AUTH_RESPONSE,
        )

        data = await cookidoo.refresh_token()
        for key, value in data.items():
            assert value == COOKIDOO_TEST_RESPONSE_AUTH_RESPONSE[key]
        assert cookidoo.expires_in > 0


class TestGetUserInfo:
    """Tests for get_user_info method."""

    async def test_get_user_info(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for get_user_info."""

        mocked.get(
            "https://ch.tmmobile.vorwerk-digital.com/community/profile",
            payload=COOKIDOO_TEST_RESPONSE_USER_INFO,
            status=HTTPStatus.OK,
        )

        data = await cookidoo.get_user_info()
        assert (
            data["username"] == COOKIDOO_TEST_RESPONSE_USER_INFO["userInfo"]["username"]  # type: ignore[index]
        )
        assert (
            data["description"]
            == COOKIDOO_TEST_RESPONSE_USER_INFO["userInfo"]["description"]  # type: ignore[index]
        )
        assert (
            data["picture"] == COOKIDOO_TEST_RESPONSE_USER_INFO["userInfo"]["picture"]  # type: ignore[index]
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
            "https://ch.tmmobile.vorwerk-digital.com/community/profile",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.get_user_info()

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.get(
            "https://ch.tmmobile.vorwerk-digital.com/community/profile",
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
            "https://ch.tmmobile.vorwerk-digital.com/community/profile",
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
            "https://ch.tmmobile.vorwerk-digital.com/ownership/subscriptions",
            payload=COOKIDOO_TEST_RESPONSE_ACTIVE_SUBSCRIPTION,
            status=HTTPStatus.OK,
        )

        data = await cookidoo.get_active_subscription()
        assert data
        assert data["active"]
        assert data["status"] == "RUNNING"

    async def test_get_inactive_subscription(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for get_active_subscription."""

        mocked.get(
            "https://ch.tmmobile.vorwerk-digital.com/ownership/subscriptions",
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
            "https://ch.tmmobile.vorwerk-digital.com/ownership/subscriptions",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.get_active_subscription()

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.get(
            "https://ch.tmmobile.vorwerk-digital.com/ownership/subscriptions",
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
            "https://ch.tmmobile.vorwerk-digital.com/ownership/subscriptions",
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
            "https://ch.tmmobile.vorwerk-digital.com/recipes/recipe/de-CH/r907015",
            payload=COOKIDOO_TEST_RESPONSE_GET_RECIPE_DETAILS,
            status=HTTPStatus.OK,
        )

        data = await cookidoo.get_recipe_details("r907015")
        assert data
        assert isinstance(data, object)
        assert data["id"] == "r907015"
        assert data["name"] == "Kokos Pralinen"
        assert isinstance(data["categories"], list)
        assert isinstance(data["collections"], list)
        assert isinstance(data["ingredients"], list)
        assert isinstance(data["notes"], list)
        assert isinstance(data["utensils"], list)
        assert isinstance(data["active_time"], int)
        assert isinstance(data["total_time"], int)
        assert isinstance(data["serving_size"], str)

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
            "https://ch.tmmobile.vorwerk-digital.com/recipes/recipe/de-CH/r907015",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.get_recipe_details("r907015")

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.get(
            "https://ch.tmmobile.vorwerk-digital.com/recipes/recipe/de-CH/r907015",
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
            "https://ch.tmmobile.vorwerk-digital.com/recipes/recipe/de-CH/r907015",
            status=status,
            body="not json",
            content_type="application/json",
        )

        with pytest.raises(exception):
            await cookidoo.get_recipe_details("r907015")


class TestGetShoppingListRecipes:
    """Tests for get_shopping_list_recipes method."""

    async def test_get_shopping_list_recipes(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for get_shopping_list_recipes."""

        mocked.get(
            "https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH",
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
            "https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.get_shopping_list_recipes()

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.get(
            "https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH",
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
            "https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH",
            status=status,
            body="not json",
            content_type="application/json",
        )

        with pytest.raises(exception):
            await cookidoo.get_shopping_list_recipes()


class TestGetIngredients:
    """Tests for get_ingredient_items method."""

    async def test_get_ingredient_items(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for get_ingredient_items."""

        mocked.get(
            "https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH",
            payload=COOKIDOO_TEST_RESPONSE_GET_INGREDIENTS,
            status=HTTPStatus.OK,
        )

        data = await cookidoo.get_ingredient_items()
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

        mocked.get(
            "https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.get_ingredient_items()

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.get(
            "https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH",
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
            "https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH",
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
            "https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH/recipes/add",
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
            "https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH/recipes/add",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.add_ingredient_items_for_recipes(["r59322", "r907016"])

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.post(
            "https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH/recipes/add",
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
            "https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH/recipes/add",
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
            "https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH/recipes/remove",
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
            "https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH/recipes/remove",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.remove_ingredient_items_for_recipes(["r59322", "r907016"])

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.post(
            "https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH/recipes/remove",
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
            "https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH/recipes/remove",
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
            "https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH/owned-ingredients/ownership/edit",
            payload=COOKIDOO_TEST_RESPONSE_EDIT_INGREDIENTS_OWNERSHIP,
            status=HTTPStatus.OK,
        )

        data = await cookidoo.edit_ingredient_items_ownership(
            [
                {
                    "id": "01JBQG02JQD3XPFMM5CXE51K25",
                    "name": "Hefe",
                    "is_owned": True,
                    "description": "1 Würfel",
                }
            ]
        )
        assert data
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["is_owned"]

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
            "https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH/owned-ingredients/ownership/edit",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.edit_ingredient_items_ownership(
                [
                    {
                        "id": "01JBQG02JQD3XPFMM5CXE51K25",
                        "name": "Hefe",
                        "is_owned": True,
                        "description": "1 Würfel",
                    }
                ]
            )

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.post(
            "https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH/owned-ingredients/ownership/edit",
            status=HTTPStatus.UNAUTHORIZED,
            payload={"error_description": ""},
        )
        with pytest.raises(CookidooAuthException):
            await cookidoo.edit_ingredient_items_ownership(
                [
                    {
                        "id": "01JBQG02JQD3XPFMM5CXE51K25",
                        "name": "Hefe",
                        "is_owned": True,
                        "description": "1 Würfel",
                    }
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
            "https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH/owned-ingredients/ownership/edit",
            status=status,
            body="not json",
            content_type="application/json",
        )

        with pytest.raises(exception):
            await cookidoo.edit_ingredient_items_ownership(
                [
                    {
                        "id": "01JBQG02JQD3XPFMM5CXE51K25",
                        "name": "Hefe",
                        "is_owned": True,
                        "description": "1 Würfel",
                    }
                ]
            )


class TestGetAdditionalItems:
    """Tests for get_additional_items method."""

    async def test_get_additional_items(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for get_additional_items."""

        mocked.get(
            "https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH",
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
            "https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.get_additional_items()

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.get(
            "https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH",
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
            "https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH",
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
            "https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH/additional-items/add",
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
            "https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH/additional-items/add",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.add_additional_items(["Fleisch", "Fisch"])

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.post(
            "https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH/additional-items/add",
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
            "https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH/additional-items/add",
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
            "https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH/additional-items/remove",
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
            "https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH/additional-items/remove",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.remove_additional_items(
                ["01JBQGDMRMR7RJW1C8AWDGD6YP", "01JBQGDMRNHAM7AMCR6YKPYKJQ"]
            )

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.post(
            "https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH/additional-items/remove",
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
            "https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH/additional-items/remove",
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
            "https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH/additional-items/ownership/edit",
            payload=COOKIDOO_TEST_RESPONSE_EDIT_ADDITIONAL_ITEMS_OWNERSHIP,
            status=HTTPStatus.OK,
        )

        data = await cookidoo.edit_additional_items_ownership(
            [
                {
                    "id": "01JBQGMGMY4KD9ZGTKAS6GQME0",
                    "name": "Fisch",
                    "is_owned": True,
                }
            ]
        )
        assert data
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["is_owned"]

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
            "https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH/additional-items/ownership/edit",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.edit_additional_items_ownership(
                [
                    {
                        "id": "01JBQGMGMY4KD9ZGTKAS6GQME0",
                        "name": "Fisch",
                        "is_owned": True,
                    }
                ]
            )

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.post(
            "https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH/additional-items/ownership/edit",
            status=HTTPStatus.UNAUTHORIZED,
            payload={"error_description": ""},
        )
        with pytest.raises(CookidooAuthException):
            await cookidoo.edit_additional_items_ownership(
                [
                    {
                        "id": "01JBQGMGMY4KD9ZGTKAS6GQME0",
                        "name": "Fisch",
                        "is_owned": True,
                    }
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
            "https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH/additional-items/ownership/edit",
            status=status,
            body="not json",
            content_type="application/json",
        )

        with pytest.raises(exception):
            await cookidoo.edit_additional_items_ownership(
                [
                    {
                        "id": "01JBQGMGMY4KD9ZGTKAS6GQME0",
                        "name": "Fisch",
                        "is_owned": True,
                    }
                ]
            )


class TestEditAdditionalItems:
    """Tests for edit_additional_items method."""

    async def test_edit_additional_items(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for edit_additional_items."""

        mocked.post(
            "https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH/additional-items/edit",
            payload=COOKIDOO_TEST_RESPONSE_EDIT_ADDITIONAL_ITEMS,
            status=HTTPStatus.OK,
        )

        data = await cookidoo.edit_additional_items(
            [
                {
                    "id": "01JBQGT72WP8Z31VCPQPT5VC6F",
                    "name": "Vogel",
                    "is_owned": True,
                }
            ]
        )
        assert data
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["name"] == "Vogel"

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
            "https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH/additional-items/edit",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.edit_additional_items(
                [
                    {
                        "id": "01JBQGT72WP8Z31VCPQPT5VC6F",
                        "name": "Vogel",
                        "is_owned": True,
                    }
                ]
            )

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.post(
            "https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH/additional-items/edit",
            status=HTTPStatus.UNAUTHORIZED,
            payload={"error_description": ""},
        )
        with pytest.raises(CookidooAuthException):
            await cookidoo.edit_additional_items(
                [
                    {
                        "id": "01JBQGT72WP8Z31VCPQPT5VC6F",
                        "name": "Vogel",
                        "is_owned": True,
                    }
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
            "https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH/additional-items/edit",
            status=status,
            body="not json",
            content_type="application/json",
        )

        with pytest.raises(exception):
            await cookidoo.edit_additional_items(
                [
                    {
                        "id": "01JBQGT72WP8Z31VCPQPT5VC6F",
                        "name": "Vogel",
                        "is_owned": True,
                    }
                ]
            )


class TestClearShoppingList:
    """Tests for clear_shopping_list method."""

    async def test_clear_shopping_list(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for clear_shopping_list."""

        mocked.delete(
            "https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH",
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
            "https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.clear_shopping_list()

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.delete(
            "https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH",
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
            "https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH",
            status=status,
            body="not json",
            content_type="application/json",
        )

        with pytest.raises(exception):
            await cookidoo.clear_shopping_list()
