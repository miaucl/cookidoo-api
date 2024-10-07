"""Unit tests for cookidoo-api."""

from dotenv import load_dotenv
from playwright.async_api import Cookie
import pytest

from cookidoo_api.cookidoo import Cookidoo

load_dotenv()

TEST_TOKEN_COOKIE = Cookie(
    {
        "domain": "cookidoo.ch",
        "name": "v-token",
        "value": "TEST_TOKEN",
        "path": "/",
        "expires": 1730845072.933648,
        "httpOnly": True,
        "secure": True,
        "sameSite": "Lax",
    }
)


@pytest.fixture(name="cookies_str")
async def cookies_str():
    """Load the cookies as str."""

    # Open and read the file
    with open("tests/test.cookies") as file:
        return file.read()


@pytest.fixture(name="cookidoo")
async def cookidoo_api_client(cookies_str):
    """Create Cookidoo instance."""

    bring = Cookidoo(cookies=cookies_str)
    return bring
