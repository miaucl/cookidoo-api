"""Get additional items."""

import logging

from playwright.async_api import Page

from cookidoo_api.actions import selector, waiter
from cookidoo_api.const import (
    SHOPPING_LIST_ADDITIONAL_CHECKED_ITEMS_SELECTOR,
    SHOPPING_LIST_ADDITIONAL_ITEM_ID_ATTR,
    SHOPPING_LIST_ADDITIONAL_ITEM_ID_SUB_SELECTOR,
    SHOPPING_LIST_ADDITIONAL_ITEM_LABEL_SUB_SELECTOR,
    SHOPPING_LIST_ADDITIONAL_ITEM_SUB_SELECTOR,
    SHOPPING_LIST_ADDITIONAL_ITEMS_SELECTOR,
)
from cookidoo_api.types import CookidooConfig, CookidooItem, CookidooItemStateType

_LOGGER = logging.getLogger(__name__)


async def get_additional_items(
    cfg: CookidooConfig,
    page: Page,
    out_dir: str,
    pending: bool = False,
    checked: bool = False,
) -> list[CookidooItem]:
    """Get additional items.

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

    additional_items: list[CookidooItem] = []

    async def items_for(sel: str, state: CookidooItemStateType) -> None:
        _LOGGER.debug("Wait for additional items: %s", sel)
        await waiter(page, sel)

        # Select the parent element
        _LOGGER.debug("Extract parent list: %s", sel)
        parent = await selector(page, sel)
        assert parent

        # Get the children of the parent element
        _LOGGER.debug(
            "Extract additional items from parent: %s / %s",
            sel,
            SHOPPING_LIST_ADDITIONAL_ITEM_SUB_SELECTOR,
        )
        children = await parent.query_selector_all(
            SHOPPING_LIST_ADDITIONAL_ITEM_SUB_SELECTOR
        )

        # Loop through the children and perform actions
        for i, child in enumerate(children):
            _logger = _LOGGER.getChild(f"{i}")
            _logger.debug("Extract elements")
            label_el, id_el = [
                await child.query_selector(item_sel)
                for item_sel in [
                    SHOPPING_LIST_ADDITIONAL_ITEM_LABEL_SUB_SELECTOR,
                    SHOPPING_LIST_ADDITIONAL_ITEM_ID_SUB_SELECTOR,
                ]
            ]

            if not id_el:
                _logger.warning(
                    "Skip as required data 'id' (%s) not found:\n%s",
                    SHOPPING_LIST_ADDITIONAL_ITEM_ID_SUB_SELECTOR,
                    await child.inner_html(),
                )
                continue
            if not label_el:
                _logger.warning(
                    "Skip as required data 'label' (%s) not found:\n%s",
                    SHOPPING_LIST_ADDITIONAL_ITEM_LABEL_SUB_SELECTOR,
                    await child.inner_html(),
                )
                continue

            _logger.debug("Extract information")
            id = await id_el.get_attribute(SHOPPING_LIST_ADDITIONAL_ITEM_ID_ATTR)
            label = await label_el.text_content()
            if not id:
                _logger.warning(
                    "Skip as id (%s) is empty:\n%s",
                    SHOPPING_LIST_ADDITIONAL_ITEM_ID_SUB_SELECTOR,
                    await id_el.inner_html(),
                )
                continue
            if not label:
                _logger.warning(
                    "Skip as label (%s) is empty:\n%s",
                    SHOPPING_LIST_ADDITIONAL_ITEM_LABEL_SUB_SELECTOR,
                    await label_el.inner_html(),
                )
                continue
            additional_item = CookidooItem(
                {
                    "label": label,
                    "description": None,
                    "id": id,
                    "state": state,
                }
            )
            _logger.debug("Data: %s", additional_item)
            additional_items.append(additional_item)

    if pending:
        _LOGGER.debug("Get pending additional items")
        await items_for(SHOPPING_LIST_ADDITIONAL_ITEMS_SELECTOR, "pending")
    if checked:
        _LOGGER.debug("Get checked additional items")
        await items_for(SHOPPING_LIST_ADDITIONAL_CHECKED_ITEMS_SELECTOR, "checked")

    return additional_items
