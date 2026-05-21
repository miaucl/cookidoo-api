"""Smoke test for cookidoo-api."""

from collections.abc import AsyncGenerator
import os
from pathlib import Path

from aiohttp import ClientSession, CookieJar
from dotenv import load_dotenv
import pytest

from cookidoo_api.cookidoo import Cookidoo
from cookidoo_api.helpers import get_localization_options
from cookidoo_api.types import CookidooConfig

load_dotenv()

COOKIE_FILE = Path(".cookies")


@pytest.fixture(name="session")
async def aiohttp_client_session() -> AsyncGenerator[ClientSession]:
    """Create  a client session."""
    jar = CookieJar(unsafe=True)
    async with ClientSession(cookie_jar=jar) as session:
        yield session


@pytest.fixture(name="cookidoo_no_auth")
async def cookidoo_api_client_no_auth(session: ClientSession) -> Cookidoo:
    """Create Cookidoo instance."""

    country = os.environ["COUNTRY"]
    localizations = await get_localization_options(country=country)

    cookidoo = Cookidoo(
        session,
        cfg=CookidooConfig(
            email=os.environ[f"EMAIL_{country.upper()}"],
            password=os.environ["PASSWORD"],
            localization=localizations[0],
        ),
    )
    return cookidoo


@pytest.fixture(name="cookidoo")
async def cookidoo_authenticated_api_client(
    session: ClientSession,
) -> Cookidoo:
    """Create authenticated Cookidoo instance from saved cookies."""

    country = os.environ["COUNTRY"]
    localizations = await get_localization_options(country=country)

    cookidoo = Cookidoo(
        session,
        cfg=CookidooConfig(
            email=os.environ[f"EMAIL_{country.upper()}"],
            password=os.environ["PASSWORD"],
            localization=localizations[0],
        ),
    )

    # Restore session from saved cookies
    cookidoo.load_cookies(COOKIE_FILE)

    return cookidoo
