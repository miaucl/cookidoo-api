"""Cookidoo landing page for automation."""

import logging
from types import TracebackType

from playwright.async_api import Browser, Cookie, Page

from cookidoo_api.const import DEFAULT_NETWORK_TIMEOUT, DEFAULT_TIMEOUT, LOGIN_START_URL
from cookidoo_api.types import CookidooConfig

_LOGGER = logging.getLogger(__name__)

EXCLUDE_RESOURCE_TYPES = ["image", "media"]


class LandingPage:
    """Cookidoo landing page for automation start and cookie set up."""

    _cfg: CookidooConfig
    _browser: Browser
    _cookies: list[Cookie]
    _page: Page
    _out_dir: str

    def __init__(
        self,
        cfg: CookidooConfig,
        browser: Browser,
        cookies: list[Cookie],
        out_dir: str = "out/prepare_landing_page",
    ):
        """Set up the landing page.

        Parameters
        ----------
        cfg
            The config for the cookidoo browser
        browser
            A browser instance
        cookies
            The cookies to load into the landing page context
        out_dir
            The directory to store the snapshots and traces

        """
        self._cfg = cfg
        self._browser = browser
        self._cookies = cookies
        self._out_dir = out_dir

    async def __aenter__(self) -> Page:
        """Open the landing page and load the cookies.

        Returns
        -------
        Page
            The landing page

        Raises
        ------
        CookidooAuthException
            When the cookies are not valid anymore

        """
        _LOGGER.debug("Create new browser context")
        context = await self._browser.new_context()

        # Set timeouts
        context.set_default_navigation_timeout(
            self._cfg.get("network_timeout", DEFAULT_NETWORK_TIMEOUT)
        )
        context.set_default_timeout(self._cfg.get("timeout", DEFAULT_TIMEOUT))

        # Enable/disable media loading
        if not self._cfg["load_media"]:
            # await context.route(
            #     re.compile(r"\.(jpg|jpeg|png|svg|gif|webp)$"),
            #     lambda route: route.abort(),
            # )
            await context.route(
                "**/*",
                lambda route: route.abort()
                if route.request.resource_type in EXCLUDE_RESOURCE_TYPES
                else route.continue_(),
            )

        # Setup tracing if configured
        if self._cfg["tracing"]:
            await context.tracing.start(screenshots=True, snapshots=True)

        # Get a new page
        _LOGGER.debug("Open page in browser context")
        self._page = await context.new_page()

        # Go to landing page
        _LOGGER.debug("Go to landing page: %s", LOGIN_START_URL)
        await self._page.goto(LOGIN_START_URL)

        # Typing will work in the future
        _LOGGER.debug("Load cookies into browser context")
        await context.add_cookies(self._cookies)  # type: ignore[arg-type]

        return self._page

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception_value: BaseException | None,
        exception_traceback: TracebackType | None,
    ) -> None:
        """Close the landing page."""
        if self._cfg["tracing"]:
            await self._page.context.tracing.stop(path=f"{self._out_dir}/trace.zip")
