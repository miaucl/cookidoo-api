"""Playwright feedback closer abstraction."""

import logging

from playwright.async_api import Page

_LOGGER = logging.getLogger(__name__)

JAVASCRIPT = """
var i = setInterval(() => {
    var el = document.querySelector('core-feedback');
    if (el) {
        el.remove();
        clearInterval(i);
    }
}, 100);
"""


async def feedback_closer(
    page: Page,
    message: str = "Cannot click on feedback close",
) -> None:
    """Click on feedback close of the core feedback modal if present.

    Parameters
    ----------
    page
        The page to search in
    message
        Human-readable message for the raised error

    Raises
    ------
    CookidooSelectorException
        When the page does not behave as expected and some content is not available

    """
    await page.evaluate(JAVASCRIPT)
