"""Unit tests for cookidoo-api."""

from typing import cast

from dotenv import load_dotenv
import pytest

from cookidoo_api.helpers import (
    build_algolia_filter_string,
    cookidoo_calendar_day_from_json,
    cookidoo_custom_recipe_from_json,
    cookidoo_recipe_details_from_json,
    cookidoo_recipe_from_json,
    cookidoo_search_recipe_hit_from_json,
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
    SearchRecipeHitJSON,
)
from cookidoo_api.types import CookidooLocalizationConfig, CookidooSearchFilters
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

    def test_cookidoo_calendar_day_from_json_with_customer_recipe_ids(self) -> None:
        """Test cookidoo_calendar_day_from_json keeps customer recipe IDs."""
        calendar_json = cast(
            CalendarDayJSON,
            COOKIDOO_TEST_RESPONSE_CALENDAR_WEEK["myDays"][0].copy(),
        )
        calendar_json["customerRecipeIds"] = ["01CUSTOMRECIPEID"]

        result = cookidoo_calendar_day_from_json(calendar_json)

        assert result.customer_recipe_ids == ["01CUSTOMRECIPEID"]

    def test_cookidoo_calendar_day_from_json_with_customer_recipes(self) -> None:
        """Test cookidoo_calendar_day_from_json includes customer recipes when present."""
        calendar_json = cast(
            CalendarDayJSON,
            COOKIDOO_TEST_RESPONSE_CALENDAR_WEEK["myDays"][0].copy(),
        )
        calendar_json["customerRecipes"] = [calendar_json["recipes"][0]]

        result = cookidoo_calendar_day_from_json(calendar_json)

        assert len(result.recipes) == 2
        assert result.recipes[0].id == "r214846"
        assert result.recipes[1].id == "r214846"


class TestSearchRecipeHitFromJson:
    """Tests for cookidoo_search_recipe_hit_from_json."""

    def test_parse_hit_with_image(self) -> None:
        """Test parsing a search hit with image template."""
        hit = cast(
            SearchRecipeHitJSON,
            {
                "id": "r130616",
                "objectID": "r130616",
                "title": "Tomaten-Knoblauch-Pasta",
                "rating": 4.1,
                "numberOfRatings": 5258,
                "totalTime": 1800,
                "image": "https://{assethost}/image/upload/{transformation}/img/recipe.jpg",
            },
        )

        result = cookidoo_search_recipe_hit_from_json(hit)

        assert result.id == "r130616"
        assert result.title == "Tomaten-Knoblauch-Pasta"
        assert result.rating == 4.1
        assert result.number_of_ratings == 5258
        assert result.total_time == 1800
        assert result.image is not None
        assert "{assethost}" not in result.image
        assert "{transformation}" not in result.image
        assert "assets.tmecosys.com" in result.image
        assert "t_web_search_380x286" in result.image

    def test_parse_hit_without_image(self) -> None:
        """Test parsing a search hit without image."""
        hit = cast(
            SearchRecipeHitJSON,
            {
                "id": "r999",
                "objectID": "r999",
                "title": "No Image Recipe",
            },
        )

        result = cookidoo_search_recipe_hit_from_json(hit)

        assert result.id == "r999"
        assert result.title == "No Image Recipe"
        assert result.rating == 0.0
        assert result.number_of_ratings == 0
        assert result.total_time == 0
        assert result.image is None

    def test_parse_hit_with_null_image(self) -> None:
        """Test parsing a search hit with null image."""
        hit = cast(
            SearchRecipeHitJSON,
            {
                "id": "r888",
                "objectID": "r888",
                "title": "Null Image Recipe",
                "rating": 3.0,
                "numberOfRatings": 10,
                "totalTime": 600,
                "image": None,
            },
        )

        result = cookidoo_search_recipe_hit_from_json(hit)

        assert result.image is None


class TestBuildAlgoliaFilterString:
    """Tests for build_algolia_filter_string."""

    def test_empty_filters(self) -> None:
        """Test with no filters set."""
        filters = CookidooSearchFilters()
        assert build_algolia_filter_string(filters) == ""

    def test_category_filter(self) -> None:
        """Test category filter."""
        filters = CookidooSearchFilters(category="VrkNavCategory-RPF-003")
        assert build_algolia_filter_string(filters) == "categories.id:VrkNavCategory-RPF-003"

    def test_difficulty_filter(self) -> None:
        """Test difficulty filter."""
        filters = CookidooSearchFilters(difficulty="easy")
        assert build_algolia_filter_string(filters) == 'difficulty:"easy"'

    def test_max_total_time_filter(self) -> None:
        """Test max total time filter."""
        filters = CookidooSearchFilters(max_total_time=1800)
        assert build_algolia_filter_string(filters) == "totalTime <= 1800"

    def test_max_prep_time_filter(self) -> None:
        """Test max prep time filter."""
        filters = CookidooSearchFilters(max_prep_time=900)
        assert build_algolia_filter_string(filters) == "preparationTime <= 900"

    def test_tm_version_filter(self) -> None:
        """Test TM version filter."""
        filters = CookidooSearchFilters(tm_version="TM6")
        assert build_algolia_filter_string(filters) == 'tmversion:"TM6"'

    def test_accessories_filter(self) -> None:
        """Test accessories filter."""
        filters = CookidooSearchFilters(accessories=["cutter", "blade_cover"])
        result = build_algolia_filter_string(filters)
        assert 'accessories:"cutter"' in result
        assert 'accessories:"blade_cover"' in result
        assert " AND " in result

    def test_portions_filter(self) -> None:
        """Test portions filter."""
        filters = CookidooSearchFilters(portions=4)
        assert build_algolia_filter_string(filters) == "portions = 4"

    def test_min_rating_filter(self) -> None:
        """Test min rating filter."""
        filters = CookidooSearchFilters(min_rating=4)
        assert build_algolia_filter_string(filters) == 'normalizedRating:"4"'

    def test_combined_filters(self) -> None:
        """Test multiple filters combined."""
        filters = CookidooSearchFilters(
            category="VrkNavCategory-RPF-003",
            difficulty="easy",
            max_total_time=1800,
        )
        result = build_algolia_filter_string(filters)
        assert "categories.id:VrkNavCategory-RPF-003" in result
        assert 'difficulty:"easy"' in result
        assert "totalTime <= 1800" in result
        assert result.count(" AND ") == 2
