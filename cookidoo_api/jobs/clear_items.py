"""Clear items."""

import logging

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from cookidoo_api.actions import clicker, selector
from cookidoo_api.const import (
    SHOPPING_LIST_CLEAR_ALL_MODAL_CONFIRM_SELECTOR,
    SHOPPING_LIST_CLEAR_ALL_OPTION_SELECTOR,
    SHOPPING_LIST_OPTIONS_SELECTOR,
)
from cookidoo_api.exceptions import CookidooSelectorException
from cookidoo_api.helpers import error_message_selector
from cookidoo_api.types import CookidooConfig

_LOGGER = logging.getLogger(__name__)


async def clear_items(
    cfg: CookidooConfig,
    page: Page,
    out_dir: str,
) -> None:
    """Clear items from list.

    This a destructive operation and cannot be undone. This remove all items, regardless of item state.

    Parameters
    ----------
    cfg
        Cookidoo config
    page
        The page, which should have been validated already
    out_dir
        The directory to store output such as trace or screenshots

    Raises
    ------
    CookidooSelectorException
        When the page does not behave as expected and some content is not available
    CookidooActionException
        When the page does not allow to perform an expected action

    """
    try:
        _LOGGER.debug(
            "Wait for list options to be visible/attached: %s , %s",
            SHOPPING_LIST_OPTIONS_SELECTOR,
            SHOPPING_LIST_CLEAR_ALL_OPTION_SELECTOR,
        )
        await page.wait_for_selector(SHOPPING_LIST_OPTIONS_SELECTOR)
        await page.wait_for_selector(
            SHOPPING_LIST_CLEAR_ALL_OPTION_SELECTOR,
            state="attached",
        )
    except PlaywrightTimeoutError as e:
        raise CookidooSelectorException(
            f"Shopping list options not found,  due to timeout.\n{error_message_selector(page.url, SHOPPING_LIST_OPTIONS_SELECTOR)}\n{error_message_selector(page.url, SHOPPING_LIST_CLEAR_ALL_OPTION_SELECTOR)}"
        ) from e

    # Get the options button and click it
    _LOGGER.debug(
        "Extract the options button: %s",
        SHOPPING_LIST_OPTIONS_SELECTOR,
    )
    options_el = await selector(page, SHOPPING_LIST_OPTIONS_SELECTOR)
    _LOGGER.debug(
        "Extract the options clear all menu option: %s",
        SHOPPING_LIST_CLEAR_ALL_OPTION_SELECTOR,
    )
    clear_all_option_el = await selector(page, SHOPPING_LIST_CLEAR_ALL_OPTION_SELECTOR)
    assert clear_all_option_el

    _LOGGER.debug(
        "Click on the options button: %s",
        SHOPPING_LIST_OPTIONS_SELECTOR,
    )
    await clicker(
        page,
        options_el,
        "Cannot click on options button of shopping list",
    )
    _LOGGER.debug(
        "Click on the options clear all menu option: %s",
        SHOPPING_LIST_CLEAR_ALL_OPTION_SELECTOR,
    )
    await clicker(
        page,
        clear_all_option_el,
        "Cannot click on clear all option in options menu of shopping list",
    )

    if cfg["screenshots"]:
        await page.screenshot(path=f"{out_dir}/2-clear-list.png")

    # Await the modal
    try:
        _LOGGER.debug(
            "Wait for the confirmation modal: %s",
            SHOPPING_LIST_CLEAR_ALL_MODAL_CONFIRM_SELECTOR,
        )
        await page.wait_for_selector(SHOPPING_LIST_CLEAR_ALL_MODAL_CONFIRM_SELECTOR)
    except PlaywrightTimeoutError as e:
        raise CookidooSelectorException(
            f"Shopping list confirm modal not found,  due to timeout.\n{error_message_selector(page.url, SHOPPING_LIST_CLEAR_ALL_MODAL_CONFIRM_SELECTOR)}"
        ) from e

    # Get the modal confirm button and click it
    _LOGGER.debug(
        "Extract the modal confirmation button: %s",
        SHOPPING_LIST_CLEAR_ALL_MODAL_CONFIRM_SELECTOR,
    )
    confirm_el = await selector(page, SHOPPING_LIST_CLEAR_ALL_MODAL_CONFIRM_SELECTOR)

    await clicker(
        page,
        confirm_el,
        "Cannot click on confirmation button in clear modal of shopping list",
    )

    # Await network stuff
    await page.wait_for_load_state(
        "networkidle"
    )  # Waits until there are no network connections for at least 500ms

    if cfg["screenshots"]:
        await page.screenshot(path=f"{out_dir}/3-clear-list-confirmed.png")
