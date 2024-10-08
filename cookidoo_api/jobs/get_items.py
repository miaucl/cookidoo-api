"""Get items."""

import logging

from playwright.async_api import Page

from cookidoo_api.actions import selector, state_waiter
from cookidoo_api.const import (
    DEFAULT_RETRIES,
    SHOPPING_LIST_CHECKED_ITEMS_SELECTOR,
    SHOPPING_LIST_EMPTY_SELECTOR,
    SHOPPING_LIST_ITEM_ID_ATTR,
    SHOPPING_LIST_ITEM_ID_SUB_SELECTOR,
    SHOPPING_LIST_ITEM_LABEL_SUB_SELECTOR,
    SHOPPING_LIST_ITEM_QUANTITY_SUB_SELECTOR,
    SHOPPING_LIST_ITEM_SUB_SELECTOR,
    SHOPPING_LIST_ITEM_UNIT_SUB_SELECTOR,
    SHOPPING_LIST_ITEMS_SELECTOR,
)
from cookidoo_api.exceptions import CookidooException
from cookidoo_api.types import CookidooConfig, CookidooItem, CookidooItemStateType

_LOGGER = logging.getLogger(__name__)


async def get_items(
    cfg: CookidooConfig,
    page: Page,
    out_dir: str,
    pending: bool = False,
    checked: bool = False,
) -> list[CookidooItem]:
    """Get items.

    Parameters
    ----------
    cfg
        Cookidoo config
    page
        The page, which should have been validated already
    out_dir
        The directory to store output such as trace or screenshots
    pending
        Get the pending items
    checked
        Get the checked items

    Returns
    -------
    list[CookidooItem]
        The list of the items

    Raises
    ------
    CookidooSelectorException
        When the page does not behave as expected and some content is not available

    """

    items: list[CookidooItem] = []

    async def items_for(sel: str, state: CookidooItemStateType) -> None:
        """Get items for a list."""
        # Await the items
        _LOGGER.debug("Wait for items: %s", sel)
        await state_waiter(page, sel, "attached")

        # Select the parent element
        _LOGGER.debug("Extract parent list: %s", sel)
        parent = await selector(page, sel)
        if await parent.is_hidden():
            _LOGGER.debug("Parent list is hidden, no items available for: %s", sel)
            return

        # Get the children of the parent element
        _LOGGER.debug(
            "Extract items from parent: %s / %s", sel, SHOPPING_LIST_ITEM_SUB_SELECTOR
        )
        children = await parent.query_selector_all(SHOPPING_LIST_ITEM_SUB_SELECTOR)

        # Loop through the children and perform actions
        for i, child in enumerate(children):
            _logger = _LOGGER.getChild(f"{i}")
            _logger.debug("Extract elements")
            label_el, quantity_el, unit_el, id_el = [
                await child.query_selector(item_sel)
                for item_sel in [
                    SHOPPING_LIST_ITEM_LABEL_SUB_SELECTOR,
                    SHOPPING_LIST_ITEM_QUANTITY_SUB_SELECTOR,
                    SHOPPING_LIST_ITEM_UNIT_SUB_SELECTOR,
                    SHOPPING_LIST_ITEM_ID_SUB_SELECTOR,
                ]
            ]

            if not id_el:
                _logger.warning(
                    "Skip as required data 'id' (%s) not found:\n%s",
                    SHOPPING_LIST_ITEM_ID_SUB_SELECTOR,
                    await child.inner_html(),
                )
                continue
            if not label_el:
                _logger.warning(
                    "Skip as required data 'label' (%s) not found:\n%s",
                    SHOPPING_LIST_ITEM_LABEL_SUB_SELECTOR,
                    await child.inner_html(),
                )
                continue

            _logger.debug("Extract information")
            id = await id_el.get_attribute(SHOPPING_LIST_ITEM_ID_ATTR)
            label = await label_el.text_content()
            quantity = await quantity_el.text_content() if quantity_el else None
            unit = await unit_el.text_content() if unit_el else None
            if not id:
                _logger.warning(
                    "Skip as id (%s) is empty:\n%s",
                    SHOPPING_LIST_ITEM_ID_SUB_SELECTOR,
                    await id_el.inner_html(),
                )
                continue
            if not label:
                _logger.warning(
                    "Skip  as label (%s) is empty:\n%s",
                    SHOPPING_LIST_ITEM_LABEL_SUB_SELECTOR,
                    await label_el.inner_html(),
                )
                continue
            item = CookidooItem(
                {
                    "label": label,
                    "description": " ".join([el for el in [quantity, unit] if el])
                    or None,
                    "id": id,
                    "state": state,
                }
            )
            _logger.debug("Data: %s", item)
            items.append(item)

    for retry in range(cfg.get("retries", DEFAULT_RETRIES)):
        try:
            items = []
            empty_list_message_el = await page.query_selector(
                SHOPPING_LIST_EMPTY_SELECTOR
            )
            if empty_list_message_el and not await empty_list_message_el.is_hidden():
                _LOGGER.debug("Lists are hidden, no items available.")
                break
            if pending:
                _LOGGER.debug("Get pending items")
                await items_for(SHOPPING_LIST_ITEMS_SELECTOR, "pending")
            if checked:
                _LOGGER.debug("Get checked items")
                await items_for(SHOPPING_LIST_CHECKED_ITEMS_SELECTOR, "checked")

            break
        except CookidooException as e:
            if retry < cfg.get("retries", DEFAULT_RETRIES):
                _LOGGER.warning(
                    "Could not get items on try #%d due to error:\n%s",
                    retry,
                    e,
                )
            else:
                _LOGGER.warning(
                    "Exhausted all #%d retries for get items",
                    retry + 1,
                )
                raise CookidooException("Could not get items") from e
    return items
