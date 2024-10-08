"""Playwright state waiter abstraction."""

from playwright.async_api import (
    ElementHandle,
    Page,
    TimeoutError as PlaywrightTimeoutError,
)

from cookidoo_api.exceptions import CookidooSelectorException
from cookidoo_api.helpers import error_message_selector
from cookidoo_api.types import CookidooWaiterStateType


async def state_waiter(
    page: Page,
    selector: str | list[str],
    state: CookidooWaiterStateType = "visible",
    message: str = "Cannot wait for element",
) -> ElementHandle | None:
    """Wait for an item and raise a standardized error if not found.

    Parameters
    ----------
    page
        The page to search in
    selector
        A single or list of selectors to iterate through
    state
        The states to wait for on the last selector
    message
        Human-readable message for the raised error

    Returns
    -------
    ElementHandle
        The element being waited for (None if state is `hidden` or `detached`)

    Raises
    ------
    ValueError
        When no selectors are are provided
    CookidooSelectorException
        When the page does not behave as expected and some content is not available

    """
    selector_list = [selector] if isinstance(selector, str) else selector
    if len(selector_list) == 0:
        raise ValueError("At least one selector must be provided.")

    parent: ElementHandle | None = None
    for i, sel in enumerate(selector_list):
        _last = len(selector_list) - 1 == i
        try:
            if parent:
                await parent.wait_for_selector(
                    sel,
                    state=state if _last else None,
                )
                next_parent = await parent.query_selector(sel) or None
            else:
                await page.wait_for_selector(
                    sel,
                    state=state if _last else None,
                )
                next_parent = await page.query_selector(sel) or None
            parent = next_parent
        except PlaywrightTimeoutError as e:
            raise CookidooSelectorException(
                f"{message}.\n{error_message_selector(page.url, selector_list[:i+1])}"
            ) from e

    return parent
