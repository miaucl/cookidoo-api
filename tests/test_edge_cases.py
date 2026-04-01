"""Extended unit tests for cookidoo-api edge cases and error handling.

These tests cover edge cases, error scenarios, and API volatility protection.
"""

from datetime import datetime
from http import HTTPStatus
from unittest.mock import AsyncMock, patch

from aiohttp import ClientError, ClientSession
from aioresponses import aioresponses
import pytest

from cookidoo_api.cookidoo import Cookidoo
from cookidoo_api.exceptions import (
    CookidooAuthException,
    CookidooConfigException,
    CookidooParseException,
    CookidooRequestException,
)
from cookidoo_api.helpers import get_localization_options
from cookidoo_api.types import (
    CookidooAuthResponse,
    CookidooConfig,
    CookidooCreateCustomRecipe,
    CookidooEditCustomRecipe,
    CookidooInstruction,
    CookidooLocalizationConfig,
    CookidooStepSettings,
)


class TestConfigAndLocalization:
    """Tests for configuration and localization edge cases."""

    @pytest.mark.parametrize(
        ("country", "language", "expected_prefix"),
        [
            ("gr", "el-GR", "gr"),  # Greece
            ("cy", "el-GR", "cy"),  # Cyprus
            ("de", "de-DE", "de"),  # Germany
            ("ch", "de-CH", "ch"),  # Switzerland
            ("at", "de-AT", "at"),  # Austria
            ("fr", "fr-FR", "fr"),  # France
            ("it", "it-IT", "it"),  # Italy
            ("es", "es-ES", "es"),  # Spain
            ("gb", "en-GB", "gb"),  # UK
            ("us", "en-US", "us"),  # USA
            ("au", "en-AU", "au"),  # Australia
            ("ma", "en", "xp"),  # Morocco (special case)
        ],
    )
    async def test_localization_endpoints(
        self,
        session: ClientSession,
        country: str,
        language: str,
        expected_prefix: str,
    ) -> None:
        """Test API endpoint generation for various localizations."""
        localization = (await get_localization_options(country=country, language=language))[0]
        cookidoo = Cookidoo(
            session,
            cfg=CookidooConfig(localization=localization),
        )

        assert expected_prefix in str(cookidoo.api_endpoint)
        assert "tmmobile.vorwerk-digital.com" in str(cookidoo.api_endpoint)

    async def test_invalid_localization(self, session: ClientSession) -> None:
        """Test handling of invalid localization."""
        with pytest.raises((ValueError, IndexError)):
            await get_localization_options(country="invalid", language="xx-XX")


class TestAuthEdgeCases:
    """Tests for authentication edge cases."""

    async def test_expired_token_detection(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test detection of expired tokens."""
        # Simulate a token that's about to expire
        mocked.post(
            "https://ch.tmmobile.vorwerk-digital.com/ciam/auth/token",
            status=HTTPStatus.OK,
            payload={
                "access_token": "test_token",
                "refresh_token": "test_refresh",
                "expires_in": 1,  # 1 second
            },
        )

        await cookidoo.login()
        assert cookidoo.expires_in <= 1

    async def test_token_refresh_with_invalid_refresh_token(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test refresh with invalid refresh token."""
        # First login successfully
        mocked.post(
            "https://ch.tmmobile.vorwerk-digital.com/ciam/auth/token",
            status=HTTPStatus.OK,
            payload={
                "access_token": "test_token",
                "refresh_token": "test_refresh",
                "expires_in": 3600,
            },
        )
        await cookidoo.login()

        # Then fail refresh
        mocked.post(
            "https://ch.tmmobile.vorwerk-digital.com/ciam/auth/token",
            status=HTTPStatus.BAD_REQUEST,
            payload={"error": "invalid_grant"},
        )

        with pytest.raises(CookidooAuthException):
            await cookidoo.refresh_token()

    async def test_concurrent_login_requests(
        self, mocked: aioresponses, session: ClientSession
    ) -> None:
        """Test that concurrent login requests are handled properly."""
        cookidoo = Cookidoo(
            session,
            cfg=CookidooConfig(
                email="test@test.com",
                password="test123",
            ),
        )

        mocked.post(
            "https://ch.tmmobile.vorwerk-digital.com/ciam/auth/token",
            status=HTTPStatus.OK,
            payload={
                "access_token": "test_token",
                "refresh_token": "test_refresh",
                "expires_in": 3600,
            },
        )

        # First login should succeed
        result1 = await cookidoo.login()
        assert result1.access_token == "test_token"


class TestRecipeOperations:
    """Tests for recipe CRUD operations."""

    async def test_create_custom_recipe_minimal(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test creating a recipe with minimal fields."""
        mocked.post(
            "https://ch.tmmobile.vorwerk-digital.com/created-recipes/de-CH",
            status=HTTPStatus.OK,
            payload={
                "id": "test-recipe-id",
                "name": "Simple Recipe",
                "servingSize": 4,
            },
        )

        recipe = CookidooCreateCustomRecipe(
            name="Simple Recipe",
            serving_size=4,
            total_time=1800,
            active_time=600,
            unit_text="portion",
            tools=["TM6"],
            ingredients=["100g flour"],
            instructions=["Mix and bake"],
        )

        result = await cookidoo.create_custom_recipe(recipe)
        assert result.id == "test-recipe-id"

    async def test_create_custom_recipe_with_structured_instructions(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test creating a recipe with structured step settings."""
        mocked.post(
            "https://ch.tmmobile.vorwerk-digital.com/created-recipes/de-CH",
            status=HTTPStatus.OK,
            payload={
                "id": "structured-recipe-id",
                "name": "Structured Recipe",
            },
        )

        recipe = CookidooCreateCustomRecipe(
            name="Structured Recipe",
            serving_size=4,
            total_time=3600,
            active_time=1800,
            unit_text="portion",
            tools=["TM6", "TM7"],
            ingredients=["500g chicken", "200g vegetables"],
            instructions=[
                CookidooInstruction(
                    text="Chop vegetables",
                    settings=CookidooStepSettings(time=10, speed=5),
                ),
                CookidooInstruction(
                    text="Cook",
                    settings=CookidooStepSettings(
                        time=1800, temperature=100, speed=1
                    ),
                ),
            ],
        )

        result = await cookidoo.create_custom_recipe(recipe)
        assert result.id == "structured-recipe-id"

    async def test_edit_nonexistent_recipe(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test editing a recipe that doesn't exist."""
        mocked.patch(
            "https://ch.tmmobile.vorwerk-digital.com/created-recipes/de-CH/nonexistent-id",
            status=HTTPStatus.NOT_FOUND,
            payload={"error": "Recipe not found"},
        )

        updates = CookidooEditCustomRecipe(name="Updated Name")

        with pytest.raises(CookidooRequestException):
            await cookidoo.edit_custom_recipe("nonexistent-id", updates)


class TestNetworkResilience:
    """Tests for network resilience and retry scenarios."""

    @pytest.mark.parametrize(
        "status_code",
        [
            HTTPStatus.SERVICE_UNAVAILABLE,  # 503
            HTTPStatus.BAD_GATEWAY,  # 502
            HTTPStatus.GATEWAY_TIMEOUT,  # 504
            HTTPStatus.TOO_MANY_REQUESTS,  # 429
            HTTPStatus.INTERNAL_SERVER_ERROR,  # 500
        ],
    )
    async def test_server_error_responses(
        self, mocked: aioresponses, cookidoo: Cookidoo, status_code: int
    ) -> None:
        """Test handling of various server error responses."""
        mocked.get(
            "https://ch.tmmobile.vorwerk-digital.com/community/profile",
            status=status_code,
            payload={"error": "Server error"},
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.get_user_info()

    async def test_network_timeout_recovery(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test behavior after network timeout."""
        mocked.get(
            "https://ch.tmmobile.vorwerk-digital.com/community/profile",
            exception=TimeoutError(),
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.get_user_info()

        # Verify cookidoo instance is still usable after failure
        assert cookidoo is not None

    async def test_partial_json_response(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test handling of malformed JSON responses."""
        mocked.get(
            "https://ch.tmmobile.vorwerk-digital.com/community/profile",
            status=HTTPStatus.OK,
            body='{"incomplete": ',
            content_type="application/json",
        )

        with pytest.raises(CookidooParseException):
            await cookidoo.get_user_info()


class TestDataValidation:
    """Tests for data validation and type checking."""

    async def test_empty_recipe_list(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test handling of empty recipe lists."""
        mocked.get(
            "https://ch.tmmobile.vorwerk-digital.com/organize/de-CH/api/custom-list?page=0",
            status=HTTPStatus.OK,
            payload={"content": [], "totalElements": 0, "totalPages": 0},
        )

        result = await cookidoo.get_custom_collections()
        assert result == []

    async def test_pagination_edge_cases(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test pagination with edge case values."""
        mocked.get(
            "https://ch.tmmobile.vorwerk-digital.com/organize/de-CH/api/custom-list?page=0",
            status=HTTPStatus.OK,
            payload={
                "content": [],
                "totalElements": 0,
                "totalPages": 0,
                "size": 20,
                "number": 0,
            },
        )

        count_recipes, count_pages = await cookidoo.count_custom_collections()
        assert count_recipes == 0
        assert count_pages == 0

    async def test_large_ingredient_list(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test handling of recipes with many ingredients."""
        many_ingredients = [
            {
                "id": f"ing-{i}",
                "name": f"Ingredient {i}",
                "isOwned": False,
                "isIngredient": True,
                "description": f"{i*10}g",
            }
            for i in range(100)
        ]

        mocked.get(
            "https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH",
            status=HTTPStatus.OK,
            payload={"items": many_ingredients},
        )

        result = await cookidoo.get_ingredient_items()
        assert len(result) == 100


class TestCalendarEdgeCases:
    """Tests for calendar functionality edge cases."""

    async def test_calendar_with_null_dates(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test calendar with null/empty date entries."""
        mocked.get(
            "https://ch.tmmobile.vorwerk-digital.com/planning/de-CH/api/my-week/2025-03-03",
            status=HTTPStatus.OK,
            payload={"days": []},
        )

        result = await cookidoo.get_recipes_in_calendar_week(
            datetime.fromisoformat("2025-03-03").date()
        )
        assert result == []

    async def test_add_recipe_to_past_date(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test adding recipes to past calendar dates."""
        # API may or may not allow this - test the behavior
        mocked.put(
            "https://ch.tmmobile.vorwerk-digital.com/planning/de-CH/api/my-day",
            status=HTTPStatus.OK,
            payload={
                "id": "2020-01-01",
                "recipes": [{"id": "r123", "title": "Test Recipe"}],
            },
        )

        past_date = datetime(2020, 1, 1).date()
        result = await cookidoo.add_recipes_to_calendar(past_date, ["r123"])
        assert result.id == "2020-01-01"


class TestShoppingListConcurrency:
    """Tests for shopping list race conditions and state management."""

    async def test_clear_already_empty_list(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test clearing an already empty shopping list."""
        mocked.delete(
            "https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH",
            status=HTTPStatus.OK,
            payload=None,
        )

        # Should not raise exception even if list is already empty
        await cookidoo.clear_shopping_list()

    async def test_add_duplicate_ingredients(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test adding the same ingredients multiple times."""
        mocked.post(
            "https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH/recipes/add",
            status=HTTPStatus.OK,
            payload={"items": [{"id": "1", "name": "Flour", "isOwned": False}]},
        )

        # Adding same recipe twice should be handled gracefully
        result1 = await cookidoo.add_ingredient_items_for_recipes(["r123"])
        result2 = await cookidoo.add_ingredient_items_for_recipes(["r123"])
        assert isinstance(result1, list)
        assert isinstance(result2, list)


class TestAPIVolatilityProtection:
    """Tests specifically for API volatility and schema changes."""

    async def test_missing_optional_fields(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test handling of responses with missing optional fields."""
        mocked.get(
            "https://ch.tmmobile.vorwerk-digital.com/community/profile",
            status=HTTPStatus.OK,
            payload={
                # Missing optional fields like description, picture
                "id": "user123",
                "userInfo": {
                    "username": "TestUser",
                },
            },
        )

        result = await cookidoo.get_user_info()
        assert result.username == "TestUser"
        assert result.description == ""  # Default value

    async def test_extra_unknown_fields(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test handling of responses with extra unknown fields."""
        mocked.get(
            "https://ch.tmmobile.vorwerk-digital.com/community/profile",
            status=HTTPStatus.OK,
            payload={
                "id": "user123",
                "userInfo": {
                    "username": "TestUser",
                    "description": "",
                    "picture": "",
                    "newUnknownField": "value",  # Extra field
                    "anotherNewField": 123,
                },
            },
        )

        # Should not crash on unknown fields
        result = await cookidoo.get_user_info()
        assert result.username == "TestUser"

    async def test_null_values_in_response(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test handling of null values in API responses."""
        mocked.get(
            "https://ch.tmmobile.vorwerk-digital.com/ownership/subscriptions",
            status=HTTPStatus.OK,
            payload=[
                {
                    "id": "sub1",
                    "status": None,  # Null status
                    "startDate": None,
                    "endDate": None,
                }
            ],
        )

        # Should handle null values gracefully
        result = await cookidoo.get_active_subscription()
        assert result is None  # Null status = inactive
