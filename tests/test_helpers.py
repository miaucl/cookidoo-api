"""Unit tests for cookidoo-api."""

from typing import cast

from dotenv import load_dotenv
import pytest

from cookidoo_api.helpers import (
    cookidoo_recipe_details_from_json,
    get_country_options,
    get_language_options,
    get_localization_options,
)
from cookidoo_api.types import RecipeDetailsJSON
from tests.responses import COOKIDOO_TEST_RESPONSE_GET_RECIPE_DETAILS

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
