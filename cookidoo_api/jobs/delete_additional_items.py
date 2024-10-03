"""Delete additional items."""

import logging

from playwright.async_api import Page

from cookidoo_api.actions import clicker, hoverer, scroller, selector, state_waiter
from cookidoo_api.const import (
    DEFAULT_RETRIES,
    DOM_CHECK_ATTACHED,
    SHOPPING_LIST_ADDITIONAL_CHECKED_ITEMS_SELECTOR,
    SHOPPING_LIST_ADDITIONAL_ITEM_DELETE_SUB_SELECTOR,
    SHOPPING_LIST_ADDITIONAL_ITEM_HOVER_SUB_SELECTOR,
    SHOPPING_LIST_ADDITIONAL_ITEMS_SELECTOR,
)
from cookidoo_api.exceptions import CookidooActionException, CookidooException
from cookidoo_api.types import CookidooConfig, CookidooItem

_LOGGER = logging.getLogger(__name__)


async def delete_additional_items(
    cfg: CookidooConfig,
    page: Page,
    out_dir: str,
    additional_items: list[CookidooItem] | list[str],
) -> None:
    """Delete additional items.

    Parameters
    ----------
    cfg
        Cookidoo config
    page
        The page, which should have been validated already
    out_dir
        The directory to store output such as trace or screenshots
    additional_items
        The additional items to delete, only the is required

    Raises
    ------
    CookidooSelectorException
        When the page does not behave as expected and some content is not available
    CookidooActionException
        When the page does not allow to perform an expected action
    CookidooUnexpectedStateException
        When something should be changes such as the state, but it is already in that state

    """

    async def delete_additional_item(i: int, additional_item_id: str) -> None:
        """Delete additional item."""
        _logger = _LOGGER.getChild(f"{i}")
        pending_sel = f'{SHOPPING_LIST_ADDITIONAL_ITEMS_SELECTOR} .additional-items-list-item:has(label[id="{additional_item_id}"])'
        checked_sel = f'{SHOPPING_LIST_ADDITIONAL_CHECKED_ITEMS_SELECTOR} .additional-items-list-item:has(label[id="{additional_item_id}"])'
        additional_item_sel = f"{pending_sel},{checked_sel}"

        _logger.debug(
            "Extract pending/checked checkbox: %s | %s",
            pending_sel,
            checked_sel,
        )
        additional_item_el = await selector(
            page,
            additional_item_sel,
            f"Additional item ({i}) {additional_item_id} not found in either list.",
        )

        # Assert still attached to DOM
        if not await additional_item_el.evaluate(DOM_CHECK_ATTACHED):
            raise CookidooActionException(
                f"Cannot interact with additional item ({i}) as it has been detached from the DOM.\n{additional_item_id}"
            )

        _logger.debug(
            "Scroll to: %s | %s",
            pending_sel,
            checked_sel,
        )
        await scroller(
            page,
            additional_item_el,
            f"Cannot scroll to additional item ({i}): {additional_item_id}",
        )
        if cfg["screenshots"]:
            await page.screenshot(
                path=f"{out_dir}/2-{i}-1-before-additional-item-delete.png"
            )

        _logger.debug(
            "Delete additional item: %s | %s",
            pending_sel,
            checked_sel,
        )

        # Hover over the first child of the additional item
        hover_el = await selector(
            page,
            [additional_item_sel, SHOPPING_LIST_ADDITIONAL_ITEM_HOVER_SUB_SELECTOR],
        )
        await hoverer(
            page,
            hover_el,
            f"Cannot hover over additional item ({i}): {additional_item_id}",
        )

        if cfg["screenshots"]:
            await page.screenshot(
                path=f"{out_dir}/2-{i}-2-hover-additional-item-delete.png"
            )

        _logger.debug("Get delete button")
        edit_el = await selector(
            page,
            [additional_item_sel, SHOPPING_LIST_ADDITIONAL_ITEM_DELETE_SUB_SELECTOR],
        )
        _logger.debug(
            "Click on delete button: %s",
            SHOPPING_LIST_ADDITIONAL_ITEM_DELETE_SUB_SELECTOR,
        )
        await clicker(
            page,
            edit_el,
            f"Cannot click on delete button of additional item ({i}): {additional_item_id}",
        )
        await state_waiter(
            page,
            additional_item_sel,
            "hidden",
            message="Item did not become hidden",
        )

        if cfg["screenshots"]:
            await page.screenshot(
                path=f"{out_dir}/2-{i}-3-after-additional-item-delete.png"
            )

        _logger.debug(
            "Delete [%s]",
            additional_item_id,
        )

    additional_item_ids = [
        additional_item if isinstance(additional_item, str) else additional_item["id"]
        for additional_item in additional_items
    ]
    for i, additional_item_id in enumerate(additional_item_ids):
        for retry in range(DEFAULT_RETRIES):
            try:
                await delete_additional_item(i, additional_item_id)
                break
            except CookidooException as e:
                if retry < DEFAULT_RETRIES:
                    _LOGGER.warning(
                        "Could not delete additional item (%d) on try #%d due to error:\n%s",
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
                        f"Cannot delete additional item ({i}) as the page did not behave as expected.\n{additional_item_id}"
                    ) from e
