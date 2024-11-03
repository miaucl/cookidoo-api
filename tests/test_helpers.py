"""Unit tests for cookidoo-api."""

from dotenv import load_dotenv

from cookidoo_api.helpers import (
    get_country_options,
    get_language_options,
    get_localization_options,
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
