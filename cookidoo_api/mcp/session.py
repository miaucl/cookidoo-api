"""Shared session management for the Cookidoo MCP server."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from aiohttp import ClientSession

from cookidoo_api.cookidoo import Cookidoo
from cookidoo_api.types import CookidooConfig

from .config import CookidooMCPConfig

type SessionFactory = Callable[[], ClientSession]
type ClientFactory = Callable[[ClientSession, CookidooConfig], Cookidoo]


class CookidooSessionManager:
    """Create and reuse an authenticated Cookidoo client for MCP tools."""

    def __init__(
        self,
        config: CookidooMCPConfig,
        session_factory: SessionFactory | None = None,
        client_factory: ClientFactory | None = None,
        refresh_buffer_seconds: int = 60,
    ) -> None:
        """Initialize the session manager."""
        self._config = config
        self._session_factory = session_factory or ClientSession
        self._client_factory = client_factory or Cookidoo
        self._refresh_buffer_seconds = refresh_buffer_seconds
        self._session: ClientSession | None = None
        self._client: Cookidoo | None = None
        self._lock = asyncio.Lock()

    async def get_client(self) -> Cookidoo:
        """Return an authenticated Cookidoo client."""
        async with self._lock:
            if self._client is None:
                await self._login_new_client()
            else:
                await self._ensure_authenticated(self._client)

            assert self._client is not None
            return self._client

    async def close(self) -> None:
        """Close the shared aiohttp session if one exists."""
        async with self._lock:
            session = self._session
            self._session = None
            self._client = None

        if session is not None and not session.closed:
            await session.close()

    async def _login_new_client(self) -> None:
        """Create a new client and log in once for the process lifetime."""
        email, password = self._config.require_credentials()
        localization = await self._config.resolve_localization()
        session = self._session_factory()
        client = self._client_factory(
            session,
            CookidooConfig(
                email=email,
                password=password,
                localization=localization,
            ),
        )

        try:
            await client.login()
        except Exception:
            if not session.closed:
                await session.close()
            raise

        self._session = session
        self._client = client

    async def _ensure_authenticated(self, client: Cookidoo) -> None:
        """Refresh authentication when a cached token is about to expire."""
        if client.auth_data is None:
            await client.login()
            return

        if client.expires_in <= self._refresh_buffer_seconds:
            await client.refresh_token()
