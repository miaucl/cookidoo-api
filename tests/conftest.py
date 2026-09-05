"""Unit tests for cookidoo-api."""

from collections.abc import AsyncGenerator, Generator

from aiohttp import ClientSession, CookieJar
from aioresponses import aioresponses
from dotenv import load_dotenv
import pytest

from cookidoo_api.cookidoo import Cookidoo
from cookidoo_api.types import CookidooConfig
from cookidoo_api.well_known import ENDPOINT_RELS

load_dotenv()

UUID = "00000000-00000000-00000000-00000000"

# Dummy OAuth2 client, so the tests do not depend on the shipped defaults.
TEST_CLIENT_ID = "test-client-id"
TEST_REDIRECT_URI = "test.cookidoo.api://code-grant"


@pytest.fixture(autouse=True)
def mock_endpoint_discovery(monkeypatch: pytest.MonkeyPatch) -> None:
    """Short-circuit .well-known/home discovery with the hardcoded shapes.

    Endpoint discovery itself is covered by tests/test_well_known.py; tests
    in this module exercise everything downstream of a successful
    resolution, so they get the const.py templates verbatim without
    needing to mock every service's .well-known/home HTTP call.
    """

    async def _resolve(*_args: object, **_kwargs: object) -> dict[str, str]:
        return {rel: template for rel, (_service, template) in ENDPOINT_RELS.items()}

    monkeypatch.setattr(
        "cookidoo_api.cookidoo.resolve_endpoint_paths",
        _resolve,
    )


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
            redirect_uri=TEST_REDIRECT_URI,
        ),
    )
    return cookidoo


@pytest.fixture(name="mocked")
def aioclient_mock() -> Generator[aioresponses]:
    """Mock Aiohttp client requests."""
    with aioresponses() as m:
        yield m
