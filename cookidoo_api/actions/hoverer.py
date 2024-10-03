"""Playwright hoverer abstraction."""

from playwright.async_api import (
    ElementHandle,
    Error as PlaywrightError,
    Page,
    TimeoutError as PlaywrightTimeoutError,
)

from cookidoo_api.exceptions import CookidooActionException, CookidooSelectorException


async def hoverer(
    page: Page,
    element: ElementHandle,
    message: str = "Cannot hover over element",
) -> None:
    """Hover over an item and raise a standardized error if not attached.

    Parameters
    ----------
    page
        The page to search in
    element
        The element to hover over
    message
        Human-readable message for the raised error

    Raises
    ------
    CookidooSelectorException
        When the page does not behave as expected and some content is not available

    """
    err_message = f"{message}.\nElement handle not found in page (or detached from DOM) for hovering.\n\tPage: {page}\n\tElement:\n\t{element}"
    if not await element.is_visible():
        raise CookidooSelectorException(err_message)
    try:
        await element.hover(timeout=3000)
    except (PlaywrightError, PlaywrightTimeoutError) as e:
        raise CookidooActionException(err_message) from e
