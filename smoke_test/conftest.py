"""Smoke test for cookidoo-api."""

from collections.abc import AsyncGenerator
import json
import os

from aiohttp import ClientSession
from dotenv import load_dotenv
import pytest

from cookidoo_api.cookidoo import Cookidoo
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

    cookidoo = Cookidoo(
        session,
        cfg=CookidooConfig(email=os.environ["EMAIL"], password=os.environ["PASSWORD"]),
    )
    return cookidoo


@pytest.fixture(name="cookidoo")
async def cookidoo_authenticated_api_client(
    session: ClientSession, auth_data: CookidooAuthResponse
) -> Cookidoo:
    """Create authenticated Cookidoo instance."""

    cookidoo = Cookidoo(
        session,
        cfg=CookidooConfig(email=os.environ["EMAIL"], password=os.environ["PASSWORD"]),
    )

    # Restore auth data from saved token
    cookidoo.auth_data = auth_data

    return cookidoo
