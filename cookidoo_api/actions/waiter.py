"""Playwright waiter abstraction."""

from playwright.async_api import (
    ElementHandle,
    Page,
    TimeoutError as PlaywrightTimeoutError,
)

from cookidoo_api.exceptions import CookidooSelectorException
from cookidoo_api.helpers import error_message_selector


async def waiter(
    page: Page,
    selector: str | list[str],
    message: str = "Cannot wait for element",
) -> ElementHandle:
    """Wait for an item and raise a standardized error if not found.

    Parameters
    ----------
    page
        The page to search in
    selector
        A single or list of selectors to iterate through
    message
        Human-readable message for the raised error

    Returns
    -------
    ElementHandle
        The element being waited for

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
        try:
            if parent:
                await parent.wait_for_selector(sel)
                next_parent = await parent.query_selector(sel) or None
            else:
                await page.wait_for_selector(sel)
                next_parent = await page.query_selector(sel) or None
            parent = next_parent
        except PlaywrightTimeoutError as e:
            raise CookidooSelectorException(
                f"{message}.\n{error_message_selector(page.url, selector_list[:i+1])}"
            ) from e

    assert parent
    return parent
