"""Update items."""

import logging

from playwright.async_api import Page

from cookidoo_api.actions import clicker, scroller, selector, waiter
from cookidoo_api.const import (
    DEFAULT_RETRIES,
    DOM_CHECK_ATTACHED,
    SHOPPING_LIST_CHECKBOX_SUB_SELECTOR,
    SHOPPING_LIST_CHECKED_ITEMS_SELECTOR,
    SHOPPING_LIST_ITEMS_SELECTOR,
)
from cookidoo_api.exceptions import CookidooActionException, CookidooException
from cookidoo_api.types import CookidooConfig, CookidooItem

_LOGGER = logging.getLogger(__name__)


async def update_items(
    cfg: CookidooConfig,
    page: Page,
    out_dir: str,
    items: list[CookidooItem],
) -> list[CookidooItem]:
    """Update items.

    Parameters
    ----------
    cfg
        Cookidoo config
    page
        The page, which should have been validated already
    out_dir
        The directory to store output such as trace or screenshots
    items
        The items to update, only the state can be changed

    Returns
    -------
    list[CookidooItem]
        The list of the items

    Raises
    ------
    CookidooSelectorException
        When the page does not behave as expected and some content is not available
    CookidooActionException
        When the page does not allow to perform an expected action
    CookidooUnexpectedStateException
        When something should be changes such as the state, but it is already in that state

    """

    async def update_item(i: int, item: CookidooItem) -> None:
        """Update item."""
        _logger = _LOGGER.getChild(f"{i}")
        pending_sel = f'{SHOPPING_LIST_ITEMS_SELECTOR} li:not(.additional-items-list-item):has(input[data-value="{item["id"]}"])'
        checked_sel = f'{SHOPPING_LIST_CHECKED_ITEMS_SELECTOR} li:not(.additional-items-list-item):has(input[data-value="{item["id"]}"])'
        item_sel = f"{pending_sel},{checked_sel}"

        _logger.debug(
            "Extract pending/checked checkbox: %s | %s",
            pending_sel,
            checked_sel,
        )
        pending_el = await page.query_selector(pending_sel)  # Can be None
        checked_el = await page.query_selector(checked_sel)  # Can be None
        item_el = await selector(
            page,
            item_sel,
            f"Item ({i}) {item['id']} not found in either list.",
        )

        # Assert still attached to DOM
        if not await item_el.evaluate(DOM_CHECK_ATTACHED):
            raise CookidooActionException(
                f"Cannot interact with item ({i}) as it has been detached from the DOM.\n{item}"
            )

        await scroller(
            page,
            item_el,
            f"Cannot scroll to item ({i}): {item}",
        )

        if cfg["screenshots"]:
            await page.screenshot(path=f"{out_dir}/2-{i}-1-before-item-update.png")

        # Handle state update
        if (
            pending_el
            and item["state"] == "checked"
            or checked_el
            and item["state"] == "pending"
        ):
            item_target_sel = pending_sel if item["state"] == "pending" else checked_sel
            _logger.debug(
                "Update state: %s | %s",
                pending_sel,
                checked_sel,
            )

            checkbox_from_el = await selector(
                page,
                [
                    item_sel,
                    SHOPPING_LIST_CHECKBOX_SUB_SELECTOR,
                ],
            )
            _logger.debug(
                "Scroll to: %s",
                item_sel,
            )
            await scroller(
                page,
                checkbox_from_el,
                f"Cannot scroll to checkbox of item ({i}): {item}",
            )

            if cfg["screenshots"]:
                await page.screenshot(
                    path=f"{out_dir}/2-{i}-2.1-before-item-state-update.png"
                )

            _logger.debug(
                "Click on checkbox and set to '%s': %s",
                item["state"],
                item_sel,
            )
            await clicker(
                page,
                checkbox_from_el,
                f"Cannot click on checkbox of item ({i}): {item}",
            )
            # Await network stuff
            await page.wait_for_load_state(
                "networkidle", timeout=3000
            )  # Waits until there are no network connections for at least 500ms
            # # Hard-coded timeout for better behaviour after heavy network related actions
            # await page.wait_for_timeout(100)

            # Await the to item
            _logger.debug(
                "Wait to be attached in the new list: %s",
                item_target_sel,
            )
            # await page.wait_for_timeout(50)
            checkbox_to_el = await waiter(
                page,
                [
                    item_target_sel,
                    SHOPPING_LIST_CHECKBOX_SUB_SELECTOR,
                ],
                message=f"Updated item ({i}) not found due to timeout: {str(item)}\nIt should now be in state '{item["state"]}' and in its respective list.",
            )

            _logger.debug(
                "Scroll to: %s",
                item_sel,
            )
            await scroller(
                page,
                checkbox_to_el,
                f"Cannot scroll to checkbox of item ({i}): {item}",
            )
            if cfg["screenshots"]:
                await page.screenshot(path=f"{out_dir}/2-{i}-2.2-after-item-update.png")

        if cfg["screenshots"]:
            await page.screenshot(path=f"{out_dir}/2-{i}-3-after-item-update.png")

        _logger.debug(
            "Set '%s' [%s] state to: %s",
            item["label"],
            item["id"],
            item["state"],
        )

    for i, item in enumerate(items):
        for retry in range(DEFAULT_RETRIES):
            try:
                await update_item(i, item)
                break
            except CookidooException as e:
                if retry < DEFAULT_RETRIES:
                    _LOGGER.warning(
                        "Could not update item (%d) on try #%d due to error:\n%s",
                        i,
                        retry,
                        e,
                    )
                else:
                    _LOGGER.warning(
                        "Exhausted all #%d retries for additional item ({%d})",
                        retry + 1,
                        i,
                    )
                    raise CookidooException(
                        f"Cannot update item ({i}) as the page did not behave as expected.\n{item}"
                    ) from e
    return items
