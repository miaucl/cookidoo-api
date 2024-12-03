"""Unit tests for cookidoo-api."""

from collections.abc import AsyncGenerator, Generator

from aiohttp import ClientSession
from aioresponses import aioresponses
from dotenv import load_dotenv
import pytest

from cookidoo_api.cookidoo import Cookidoo

load_dotenv()

UUID = "00000000-00000000-00000000-00000000"


@pytest.fixture(name="session")
async def aiohttp_client_session() -> AsyncGenerator[ClientSession]:
    """Create  a client session."""
    async with ClientSession() as session:
        yield session


@pytest.fixture(name="cookidoo")
async def bring_api_client(session: ClientSession) -> Cookidoo:
    """Create Cookidoo instance."""
    bring = Cookidoo(session)
    return bring


@pytest.fixture(name="mocked")
def aioclient_mock() -> Generator[aioresponses]:
    """Mock Aiohttp client requests."""
    with aioresponses() as m:
        yield m
