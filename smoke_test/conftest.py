"""Smoke test for cookidoo-api."""

from collections.abc import AsyncGenerator
import os

from aiohttp import ClientSession
from dotenv import load_dotenv
import pytest

from cookidoo_api.const import DEFAULT_COOKIDOO_CONFIG
from cookidoo_api.cookidoo import Cookidoo

load_dotenv()


@pytest.fixture(name="session")
async def aiohttp_client_session() -> AsyncGenerator[ClientSession]:
    """Create  a client session."""
    async with ClientSession() as session:
        yield session


@pytest.fixture(name="cookidoo")
async def cookidoo_api_client(session: ClientSession) -> Cookidoo:
    """Create Cookidoo instance."""

    cookidoo = Cookidoo(
        session,
        {
            **DEFAULT_COOKIDOO_CONFIG,
            "email": os.environ["EMAIL"],
            "password": os.environ["PASSWORD"],
        },
    )
    return cookidoo


@pytest.fixture(name="cookidoo_auth")
async def cookidoo_authenticated_api_client(cookidoo: Cookidoo) -> Cookidoo:
    """Create authenticated Cookidoo instance."""

    await cookidoo.login()
    return cookidoo
