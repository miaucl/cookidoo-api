"""Cookidoo shopping list for automation."""

import logging
from types import TracebackType

from playwright.async_api import Page

from cookidoo_api.actions import feedback_closer, waiter
from cookidoo_api.const import SHOPPING_LIST_SELECTOR, SHOPPING_LIST_URL
from cookidoo_api.types import CookidooConfig

_LOGGER = logging.getLogger(__name__)


class ShoppingList:
    """Cookidoo shopping list for automation."""

    _cfg: CookidooConfig
    _page: Page
    _out_dir: str

    def __init__(
        self,
        cfg: CookidooConfig,
        page: Page,
        out_dir: str = "out/shopping_list",
    ):
        """Open the shopping list.

        Parameters
        ----------
        cfg
            The config for the cookidoo browser
        page
            A page instance
        out_dir
            The directory to store the snapshots and traces

        """
        self._cfg = cfg
        self._page = page
        self._out_dir = out_dir

    async def __aenter__(self) -> Page:
        """Open the shopping list.

        Returns
        -------
        Page
            The shopping list page

        Raises
        ------
        CookidooSelectorException
            When it was not possible to open the shopping list

        """
        # Go to shopping list
        _LOGGER.debug("Go to shopping list: %s", SHOPPING_LIST_URL)
        await self._page.goto(SHOPPING_LIST_URL)

        # Load script to close feedback modal
        await feedback_closer(self._page)

        # Take a screenshot of the shopping list
        if self._cfg["screenshots"]:
            await self._page.screenshot(path=f"{self._out_dir}/1-shopping-list.png")

        # Await the shopping list
        _LOGGER.debug("Wait for shopping list to load: %s", SHOPPING_LIST_SELECTOR)
        await waiter(self._page, SHOPPING_LIST_SELECTOR)

        return self._page

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception_value: BaseException | None,
        exception_traceback: TracebackType | None,
    ) -> None:
        """Close the shopping list."""
        pass
