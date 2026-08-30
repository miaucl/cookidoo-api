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

TOKEN_FILE = Path(".token")
COOKIE_FILE = Path(".cookies")

# Selects which login method the two-stage smoke test batch exercises:
# "oauth" (default, the preferred method) or "cookie" (the fallback used when
# no OAuth2 client credentials are configured). Set by the workflow so the
# same test_2_methods.py suite can be run against either persisted session.
AUTH_MODE = os.environ.get("AUTH_MODE", "oauth")


@pytest.fixture(name="session")
async def aiohttp_client_session() -> AsyncGenerator[ClientSession]:
    """Create  a client session."""
    jar = CookieJar(unsafe=True)
    async with ClientSession(cookie_jar=jar) as session:
        yield session


@pytest.fixture(name="cookidoo_no_auth")
async def cookidoo_api_client_no_auth(session: ClientSession) -> Cookidoo:
    """Create Cookidoo instance for the OAuth2 login (stage 1, primary)."""

    country = os.environ["COUNTRY"]
    localizations = await get_localization_options(country=country)

    cookidoo = Cookidoo(
        session,
        cfg=CookidooConfig(
            email=os.environ[f"EMAIL_{country.upper()}"],
            password=os.environ["PASSWORD"],
            client_id=os.environ["CLIENT_ID"],
            client_secret=os.environ["CLIENT_SECRET"],
            redirect_uri=os.environ["REDIRECT_URI"],
            localization=localizations[0],
        ),
    )
    return cookidoo


@pytest.fixture(name="cookidoo_no_auth_cookie")
async def cookidoo_api_client_no_auth_cookie(session: ClientSession) -> Cookidoo:
    """Create Cookidoo instance for the cookie-session login (stage 1, fallback).

    No OAuth2 client credentials are configured, so ``login()`` falls back to
    the legacy cookie-session flow.
    """

    country = os.environ["COUNTRY"]
    localizations = await get_localization_options(country=country)

    return Cookidoo(
        session,
        cfg=CookidooConfig(
            email=os.environ[f"EMAIL_{country.upper()}"],
            password=os.environ["PASSWORD"],
            localization=localizations[0],
        ),
    )


@pytest.fixture(name="cookidoo")
async def cookidoo_authenticated_api_client(
    session: ClientSession,
) -> Cookidoo:
    """Create authenticated Cookidoo instance from a saved session (stage 2).

    Restores either the OAuth2 token or the cookie-session, depending on
    ``AUTH_MODE``, so the same test suite runs against both login methods.
    """

    country = os.environ["COUNTRY"]
    localizations = await get_localization_options(country=country)

    # The OAuth2 client credentials are only needed to log in or to refresh the
    # access token, not to restore a still valid one, so they are optional here
    # (the PR smoke test intentionally runs this stage without secrets).
    cookidoo = Cookidoo(
        session,
        cfg=CookidooConfig(
            email=os.environ[f"EMAIL_{country.upper()}"],
            password=os.environ["PASSWORD"],
            client_id=os.environ.get("CLIENT_ID", ""),
            client_secret=os.environ.get("CLIENT_SECRET", ""),
            redirect_uri=os.environ.get("REDIRECT_URI", ""),
            localization=localizations[0],
        ),
    )

    if AUTH_MODE == "cookie":
        # Restore session from saved cookies
        cookidoo.load_cookies(COOKIE_FILE)
    else:
        # Restore session from a saved token
        cookidoo.load_token(TOKEN_FILE)

    return cookidoo
