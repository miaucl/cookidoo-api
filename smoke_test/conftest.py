"""Smoke test for cookidoo-api."""

from collections.abc import AsyncGenerator
import json
import os

from aiohttp import ClientSession
from dotenv import load_dotenv
import pytest

from cookidoo_api.cookidoo import Cookidoo
from cookidoo_api.helpers import get_localization_options
from cookidoo_api.types import CookidooAuthResponse, CookidooConfig

load_dotenv()


def save_token(token: CookidooAuthResponse) -> None:
    """Save the token locally."""
    with open(".token", "w", encoding="utf-8") as file:
        file.write(json.dumps(token.__dict__))


def load_token() -> CookidooAuthResponse:
    """Load the token locally."""
    # Open and read the file
    with open(".token", encoding="utf-8") as file:
        token = file.read()
        return CookidooAuthResponse(**json.loads(token))


@pytest.fixture(name="auth_data")
async def auth_data() -> CookidooAuthResponse:
    """Load the token."""

    return load_token()


@pytest.fixture(name="session")
async def aiohttp_client_session() -> AsyncGenerator[ClientSession]:
    """Create  a client session."""
    async with ClientSession() as session:
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
    session: ClientSession, auth_data: CookidooAuthResponse
) -> Cookidoo:
    """Create authenticated Cookidoo instance."""

    country = os.environ["COUNTRY"]
    localizations = await get_localization_options(country=country)

    print(
        CookidooConfig(
            email=os.environ[f"EMAIL_{country.upper()}"],
            password=os.environ["PASSWORD"],
            localization=localizations[0],
        )
    )
    cookidoo = Cookidoo(
        session,
        cfg=CookidooConfig(
            email=os.environ[f"EMAIL_{country.upper()}"],
            password=os.environ["PASSWORD"],
            localization=localizations[0],
        ),
    )

    # Restore auth data from saved token
    cookidoo.auth_data = auth_data

    return cookidoo
