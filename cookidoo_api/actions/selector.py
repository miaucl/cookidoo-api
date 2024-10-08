"""Playwright selector abstraction."""

from playwright.async_api import ElementHandle, Page

from cookidoo_api.exceptions import CookidooSelectorException
from cookidoo_api.helpers import error_message_selector


async def selector(
    page: Page, selector: str | list[str], message: str = "Cannot select element"
) -> ElementHandle:
    """Select an item and raise a standardized error if not found.

    Parameters
    ----------
    page
        The page to search in
    selector
        A single or list of selectors to iterate through and return the last element handle
    message
        Human-readable message for the raised error

    Returns
    -------
    ElementHandle
        The element being selected

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
        if parent:
            parent = await parent.query_selector(sel)
        else:
            parent = await page.query_selector(sel)

        if not parent:
            raise CookidooSelectorException(
                f"{message}.\n{error_message_selector(page.url, selector_list[:i+1])}"
            )

    assert parent
    return parent
