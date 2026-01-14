"""Unit tests for cookidoo-api."""

from typing import cast

from dotenv import load_dotenv
import pytest

from cookidoo_api.helpers import (
    cookidoo_calendar_day_from_json,
    cookidoo_custom_recipe_from_json,
    cookidoo_recipe_details_from_json,
    cookidoo_recipe_from_json,
    get_country_options,
    get_language_options,
    get_localization_options,
)
from cookidoo_api.raw_types import (
    CalendarDayJSON,
    CustomRecipeJSON,
    DescriptiveAssetJSON,
    RecipeDetailsJSON,
    RecipeJSON,
)
from cookidoo_api.types import CookidooLocalizationConfig
from tests.responses import (
    COOKIDOO_TEST_RESPONSE_CALENDAR_WEEK,
    COOKIDOO_TEST_RESPONSE_GET_CUSTOM_RECIPE,
    COOKIDOO_TEST_RESPONSE_GET_RECIPE_DETAILS,
    COOKIDOO_TEST_RESPONSE_GET_SHOPPING_LIST_RECIPES,
)

load_dotenv()


class TestLocalization:
    """Tests for localization functions."""

    async def test_get_localization_options(self) -> None:
        """Test get localization options."""
        assert len(await get_localization_options()) == 373
        assert len(await get_localization_options(country="ch")) == 4
        assert len(await get_localization_options(language="en")) == 38

    async def test_get_country_options(self) -> None:
        """Test get country options."""
        assert len(await get_country_options()) == 54

    async def test_get_language_options(self) -> None:
        """Test get language options."""
        assert len(await get_language_options()) == 31

    async def test_cookidoo_recipe_details_from_json_exception(self) -> None:
        """Test get recipe details from json exception."""
        JSON = cast(RecipeDetailsJSON, COOKIDOO_TEST_RESPONSE_GET_RECIPE_DETAILS.copy())
        JSON["times"] = []

        with pytest.raises(StopIteration):
            cookidoo_recipe_details_from_json(JSON)


class TestRecipeImagesAndUrls:
    """Tests for recipe image and URL extraction."""

    def test_cookidoo_recipe_from_json_with_images(self) -> None:
        """Test cookidoo_recipe_from_json extracts images correctly."""
        recipe_json = cast(
            RecipeJSON,
            COOKIDOO_TEST_RESPONSE_GET_SHOPPING_LIST_RECIPES["recipes"][0].copy(),
        )
        localization = CookidooLocalizationConfig(
            country_code="ch", language="de-CH", url="https://cookidoo.ch"
        )

        result = cookidoo_recipe_from_json(recipe_json, localization)

        assert result.thumbnail is not None
        assert result.image is not None
        assert "{transformation}" not in result.thumbnail
        assert "{transformation}" not in result.image
        assert "t_web_shared_recipe_221x240" in result.thumbnail
        assert "t_web_rdp_recipe_584x480_1_5x" in result.image
        assert result.url == "https://cookidoo.ch/recipes/recipe/de-CH/r907016"

    def test_cookidoo_recipe_from_json_without_images_object(self) -> None:
        """Test cookidoo_recipe_from_json handles missing images object."""
        recipe_json = cast(
            RecipeJSON,
            COOKIDOO_TEST_RESPONSE_GET_SHOPPING_LIST_RECIPES["recipes"][0].copy(),
        )
        recipe_json["descriptiveAssets"] = None
        localization = CookidooLocalizationConfig(
            country_code="ch", language="de-CH", url="https://cookidoo.ch"
        )

        result = cookidoo_recipe_from_json(recipe_json, localization)

        assert result.thumbnail is None
        assert result.image is None
        assert result.url == "https://cookidoo.ch/recipes/recipe/de-CH/r907016"

    def test_cookidoo_recipe_from_json_with_empty_images(self) -> None:
        """Test cookidoo_recipe_from_json handles empty images list."""
        recipe_json = cast(
            RecipeJSON,
            COOKIDOO_TEST_RESPONSE_GET_SHOPPING_LIST_RECIPES["recipes"][0].copy(),
        )
        recipe_json["descriptiveAssets"] = []
        localization = CookidooLocalizationConfig(
            country_code="ch", language="de-CH", url="https://cookidoo.ch"
        )

        result = cookidoo_recipe_from_json(recipe_json, localization)

        assert result.thumbnail is None
        assert result.image is None
        assert result.url == "https://cookidoo.ch/recipes/recipe/de-CH/r907016"

    def test_cookidoo_recipe_from_json_with_no_image_variantes(self) -> None:
        """Test cookidoo_recipe_from_json handles no image variants."""
        recipe_json = cast(
            RecipeJSON,
            COOKIDOO_TEST_RESPONSE_GET_SHOPPING_LIST_RECIPES["recipes"][0].copy(),
        )
        recipe_json["descriptiveAssets"] = [cast(DescriptiveAssetJSON, {})]
        localization = CookidooLocalizationConfig(
            country_code="ch", language="de-CH", url="https://cookidoo.ch"
        )

        result = cookidoo_recipe_from_json(recipe_json, localization)

        assert result.thumbnail is None
        assert result.image is None
        assert result.url == "https://cookidoo.ch/recipes/recipe/de-CH/r907016"

    def test_cookidoo_recipe_from_json_without_localization(self) -> None:
        """Test cookidoo_recipe_from_json handles missing localization."""
        recipe_json = cast(
            RecipeJSON,
            COOKIDOO_TEST_RESPONSE_GET_SHOPPING_LIST_RECIPES["recipes"][0].copy(),
        )

        result = cookidoo_recipe_from_json(recipe_json, None)

        assert result.url == ""

    def test_cookidoo_recipe_details_from_json_with_images(self) -> None:
        """Test cookidoo_recipe_details_from_json extracts images correctly."""
        recipe_json = cast(
            RecipeDetailsJSON,
            COOKIDOO_TEST_RESPONSE_GET_RECIPE_DETAILS.copy(),
        )
        localization = CookidooLocalizationConfig(
            country_code="ch", language="de-CH", url="https://cookidoo.ch"
        )

        result = cookidoo_recipe_details_from_json(recipe_json, localization)

        assert result.thumbnail is not None
        assert result.image is not None
        assert "{transformation}" not in result.thumbnail
        assert "{transformation}" not in result.image
        assert "t_web_shared_recipe_221x240" in result.thumbnail
        assert "t_web_rdp_recipe_584x480_1_5x" in result.image
        assert result.url == "https://cookidoo.ch/recipes/recipe/de-CH/r907015"

    def test_cookidoo_recipe_details_from_json_without_images(self) -> None:
        """Test cookidoo_recipe_details_from_json handles missing images."""
        recipe_json = cast(
            RecipeDetailsJSON,
            COOKIDOO_TEST_RESPONSE_GET_RECIPE_DETAILS.copy(),
        )
        recipe_json["descriptiveAssets"] = None
        localization = CookidooLocalizationConfig(
            country_code="ch", language="de-CH", url="https://cookidoo.ch"
        )

        result = cookidoo_recipe_details_from_json(recipe_json, localization)

        assert result.thumbnail is None
        assert result.image is None
        assert result.url == "https://cookidoo.ch/recipes/recipe/de-CH/r907015"

    def test_cookidoo_custom_recipe_from_json_with_image(self) -> None:
        """Test cookidoo_custom_recipe_from_json extracts image correctly."""
        recipe_json = cast(
            CustomRecipeJSON,
            COOKIDOO_TEST_RESPONSE_GET_CUSTOM_RECIPE.copy(),
        )
        localization = CookidooLocalizationConfig(
            country_code="ch", language="de-CH", url="https://cookidoo.ch"
        )

        result = cookidoo_custom_recipe_from_json(recipe_json, localization)

        assert result.thumbnail is not None
        assert result.image is not None
        assert "{transformation}" not in result.thumbnail
        assert "{transformation}" not in result.image
        assert "t_web_shared_recipe_221x240" in result.thumbnail
        assert "t_web_rdp_recipe_584x480_1_5x" in result.image
        assert (
            result.url
            == "https://cookidoo.ch/created-recipes/de-CH/01K2CVHD1DXG1PVETNVV3JPKWW"
        )

    def test_cookidoo_custom_recipe_from_json_without_image(self) -> None:
        """Test cookidoo_custom_recipe_from_json handles missing image."""
        recipe_json = cast(
            CustomRecipeJSON,
            COOKIDOO_TEST_RESPONSE_GET_CUSTOM_RECIPE.copy(),
        )
        recipe_json["recipeContent"]["image"] = None
        localization = CookidooLocalizationConfig(
            country_code="ch", language="de-CH", url="https://cookidoo.ch"
        )

        result = cookidoo_custom_recipe_from_json(recipe_json, localization)

        assert result.thumbnail is None
        assert result.image is None
        assert (
            result.url
            == "https://cookidoo.ch/created-recipes/de-CH/01K2CVHD1DXG1PVETNVV3JPKWW"
        )

    def test_cookidoo_calendar_day_from_json_with_images(self) -> None:
        """Test cookidoo_calendar_day_from_json extracts images correctly."""
        calendar_json = cast(
            CalendarDayJSON,
            COOKIDOO_TEST_RESPONSE_CALENDAR_WEEK["myDays"][0].copy(),
        )
        localization = CookidooLocalizationConfig(
            country_code="ch", language="de-CH", url="https://cookidoo.ch"
        )

        result = cookidoo_calendar_day_from_json(calendar_json, localization)

        assert len(result.recipes) > 0
        recipe = result.recipes[0]
        assert recipe.thumbnail is not None
        assert recipe.image is not None
        assert "{transformation}" not in recipe.thumbnail
        assert "{transformation}" not in recipe.image
        assert "t_web_shared_recipe_221x240" in recipe.thumbnail
        assert "t_web_rdp_recipe_584x480_1_5x" in recipe.image
        assert recipe.url == "https://cookidoo.ch/recipes/recipe/de-CH/r214846"

    def test_cookidoo_calendar_day_from_json_without_images(self) -> None:
        """Test cookidoo_calendar_day_from_json handles missing images."""
        calendar_json = cast(
            CalendarDayJSON,
            COOKIDOO_TEST_RESPONSE_CALENDAR_WEEK["myDays"][0].copy(),
        )
        calendar_json["recipes"][0]["assets"] = None
        localization = CookidooLocalizationConfig(
            country_code="ch", language="de-CH", url="https://cookidoo.ch"
        )

        result = cookidoo_calendar_day_from_json(calendar_json, localization)

        assert len(result.recipes) > 0
        recipe = result.recipes[0]
        assert recipe.thumbnail is None
        assert recipe.image is None
        assert recipe.url == "https://cookidoo.ch/recipes/recipe/de-CH/r214846"
