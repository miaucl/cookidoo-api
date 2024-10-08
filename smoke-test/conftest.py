"""Smoke test for cookidoo-api."""

import os

from dotenv import load_dotenv
import pytest

from cookidoo_api.const import DEFAULT_COOKIDOO_CONFIG
from cookidoo_api.cookidoo import Cookidoo

load_dotenv()

TEST_RECIPE = "r59322"
TEST_ITEMS_COUNT = 7
TEST_ITEM_LABEL = "Wasser"
TEST_ITEM_DESCRIPTION = "220 g"
TEST_ADDITIONAL_ITEM_CREATE = ["Schokolade", "Apfel", "Orange", "Mehl"]
TEST_ADDITIONAL_ITEM_LABEL = TEST_ADDITIONAL_ITEM_CREATE[0]


def save_cookies(cookies: str):
    """Save the cookies locally."""
    with open(".cookies", "w") as file:
        file.write(cookies)


def load_cookies() -> str:
    """Load the cookies locally."""
    # Open and read the file
    with open(".cookies") as file:
        return file.read()


@pytest.fixture(name="cookies_str")
async def cookies_str():
    """Load the cookies as str."""

    return load_cookies()


@pytest.fixture(name="cookidoo")
async def cookidoo_api_client(cookies_str):
    """Create Cookidoo instance."""

    cookidoo = Cookidoo(
        {
            **DEFAULT_COOKIDOO_CONFIG,
            # Use local headless executable
            "browser": "chromium",
            "headless": True,
            # Do not load media
            "load_media": False,
            # Load credentials from env
            "email": os.environ["EMAIL"],
            "password": os.environ["PASSWORD"],
            # Enable tracing
            "tracing": True,
            "screenshots": True,
        },
        cookies_str,
    )
    return cookidoo
