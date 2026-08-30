"""Unit tests for cookidoo-api."""

from collections.abc import AsyncGenerator, Generator

from aiohttp import ClientSession, CookieJar
from aioresponses import aioresponses
from dotenv import load_dotenv
import pytest

from cookidoo_api.cookidoo import Cookidoo
from cookidoo_api.types import CookidooConfig

load_dotenv()

UUID = "00000000-00000000-00000000-00000000"

# Dummy OAuth2 client, the real credentials are not part of this repository.
TEST_CLIENT_ID = "test-client-id"
TEST_CLIENT_SECRET = "test-client-secret"
TEST_REDIRECT_URI = "test.cookidoo.api://code-grant"


@pytest.fixture(name="session")
async def aiohttp_client_session() -> AsyncGenerator[ClientSession]:
    """Create  a client session."""
    jar = CookieJar(unsafe=True)
    async with ClientSession(cookie_jar=jar) as session:
        yield session


@pytest.fixture(name="cookidoo")
async def bring_api_client(session: ClientSession) -> Cookidoo:
    """Create Cookidoo instance."""
    cookidoo = Cookidoo(
        session,
        cfg=CookidooConfig(
            client_id=TEST_CLIENT_ID,
            client_secret=TEST_CLIENT_SECRET,
            redirect_uri=TEST_REDIRECT_URI,
        ),
    )
    return cookidoo


@pytest.fixture(name="cookidoo_cookie")
async def bring_api_client_cookie(session: ClientSession) -> Cookidoo:
    """Create Cookidoo instance without OAuth2 client credentials.

    Since no client credentials are configured, ``login()`` falls back to the
    legacy cookie-session flow.
    """
    return Cookidoo(session)


@pytest.fixture(name="mocked")
def aioclient_mock() -> Generator[aioresponses]:
    """Mock Aiohttp client requests."""
    with aioresponses() as m:
        yield m
