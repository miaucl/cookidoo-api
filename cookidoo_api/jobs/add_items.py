"""Add items."""

import logging

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from cookidoo_api.actions import clicker, scroller, selector, waiter
from cookidoo_api.const import (
    DEFAULT_RETRIES,
    RECEIPT_ADD_OPTION_SHOPPING_LIST_SELECTOR,
    RECEIPT_ADD_OPTIONS_SELECTOR_TEMPLATE,
    RECEIPT_ADD_TO_SHOPPING_LIST_CONFIRM_SELECTOR,
    RECEIPT_URL_PREFIX,
)
from cookidoo_api.exceptions import CookidooException, CookidooNavigationException
from cookidoo_api.helpers import error_message_selector
from cookidoo_api.types import CookidooConfig

_LOGGER = logging.getLogger(__name__)


async def add_items(
    cfg: CookidooConfig,
    page: Page,
    receipt_id: str,
    out_dir: str,
) -> None:
    """Add items to list from receipt.

    Parameters
    ----------
    cfg
        Cookidoo config
    page
        The page, which should have been validated already
    receipt_id
        The id of the receipt to add the items to the shopping list
    out_dir
        The directory to store output such as trace or screenshots

    Raises
    ------
    CookidooNavigationException
        When the page could not be found
    CookidooSelectorException
        When the page does not behave as expected and some content is not available
    CookidooActionException
        When the page does not allow to perform an expected action

    """
    for retry in range(cfg.get("retries", DEFAULT_RETRIES)):
        try:
            try:
                # Go to receipt page
                _LOGGER.debug(
                    "Go to receipt page: %s%s", RECEIPT_URL_PREFIX, receipt_id
                )
                await page.goto(f"{RECEIPT_URL_PREFIX}{receipt_id}")

                _LOGGER.debug(
                    "Wait for add options to be visible/attached: %s",
                    RECEIPT_ADD_OPTIONS_SELECTOR_TEMPLATE.format(receipt_id),
                )
                await page.wait_for_selector(
                    RECEIPT_ADD_OPTIONS_SELECTOR_TEMPLATE.format(receipt_id)
                )
            except PlaywrightTimeoutError as e:
                raise CookidooNavigationException(
                    f"Receipt page not found, due to timeout.\n{error_message_selector(page.url, RECEIPT_ADD_OPTIONS_SELECTOR_TEMPLATE.format(receipt_id))}"
                ) from e

            if cfg["screenshots"]:
                await page.screenshot(path=f"{out_dir}/1-receipt.png")

            _LOGGER.debug(
                "Extract the options button: %s",
                RECEIPT_ADD_OPTIONS_SELECTOR_TEMPLATE.format(receipt_id),
            )
            options_el = await selector(
                page, RECEIPT_ADD_OPTIONS_SELECTOR_TEMPLATE.format(receipt_id)
            )
            await scroller(page, options_el)

            if cfg["screenshots"]:
                await page.screenshot(path=f"{out_dir}/2-receipt-add-options.png")

            _LOGGER.debug(
                "Click on options button: %s",
                RECEIPT_ADD_OPTIONS_SELECTOR_TEMPLATE.format(receipt_id),
            )
            await clicker(
                page,
                options_el,
                "Cannot click on add options button of receipt",
            )

            if cfg["screenshots"]:
                await page.screenshot(
                    path=f"{out_dir}/3-receipt-add-options-dropdown.png"
                )

            _LOGGER.debug(
                "Extract the shopping list option button: %s",
                RECEIPT_ADD_OPTION_SHOPPING_LIST_SELECTOR,
            )
            shopping_list_option_el = await selector(
                page, RECEIPT_ADD_OPTION_SHOPPING_LIST_SELECTOR
            )

            _LOGGER.debug(
                "Click on shopping list option button: %s",
                RECEIPT_ADD_OPTION_SHOPPING_LIST_SELECTOR,
            )
            await clicker(
                page,
                shopping_list_option_el,
                "Cannot click on shopping list option button of receipt",
            )

            # Await network stuff
            await page.wait_for_load_state(
                "networkidle"
            )  # Waits until there are no network connections for at least 500ms

            await waiter(page, RECEIPT_ADD_TO_SHOPPING_LIST_CONFIRM_SELECTOR)

            if cfg["screenshots"]:
                await page.screenshot(path=f"{out_dir}/4-receipt-items-added.png")
            break
        except CookidooException as e:
            if retry < cfg.get("retries", DEFAULT_RETRIES):
                _LOGGER.warning(
                    "Could not add items of receipt (%s) on try #%d due to error:\n%s",
                    receipt_id,
                    retry,
                    e,
                )
            else:
                _LOGGER.warning(
                    "Exhausted all #%d retries for add items (%s)",
                    retry + 1,
                    receipt_id,
                )
                raise CookidooException(
                    f"Could not add items of receipt ({receipt_id})"
                ) from e
