"""Cookidoo browser for automation."""

import logging
from types import TracebackType

from playwright.async_api import Browser, Playwright

from cookidoo_api.exceptions import CookidooConfigException
from cookidoo_api.helpers import resolve_remote_addr
from cookidoo_api.types import CookidooConfig

_LOGGER = logging.getLogger(__name__)


class CookidooBrowser:
    """Cookidoo browser for automation."""

    _cfg: CookidooConfig
    _playwright: Playwright
    _browser: Browser

    def __init__(self, cfg: CookidooConfig, playwright: Playwright):
        """Initialize the playwright browser.

        Parameters
        ----------
        cfg
            The config for the cookidoo browser
        playwright
            A playwright instance

        """
        self._playwright = playwright
        self._cfg = cfg

    async def __aenter__(self) -> Browser:
        """Open the browser.

        Returns
        -------
        Browser
            The browser

        Raises
        ------
        CookidooConfigException
            Browser not recognized

        """
        if not hasattr(self._playwright, self._cfg["browser"]):
            raise CookidooConfigException(
                f"Browser '{self._cfg["browser"]}' not recognized"
            )

        if not self._cfg["remote_addr"]:
            _LOGGER.debug(
                "Set up browser [%s] with headless=%d",
                self._cfg["browser"],
                self._cfg["headless"],
            )
            self._browser = await self._playwright[self._cfg["browser"]].launch(
                headless=self._cfg["headless"]
            )
        else:
            resolved_connection_url = f"http://{resolve_remote_addr(self._cfg["remote_addr"])}:{self._cfg["remote_port"]}"
            _LOGGER.debug(
                "Connection to browser [%s] on remote runner: %s",
                self._cfg["browser"],
                resolved_connection_url,
            )
            self._browser = await self._playwright[
                self._cfg["browser"]
            ].connect_over_cdp(resolved_connection_url)
        return self._browser

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception_value: BaseException | None,
        exception_traceback: TracebackType | None,
    ) -> None:
        """Close the browser."""
        _LOGGER.debug(
            "Close browser [%s]",
            self._cfg["browser"],
        )
        await self._browser.close()
