"""Create additional items."""

import logging

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from cookidoo_api.actions import clicker, scroller, selector, waiter
from cookidoo_api.const import (
    DEFAULT_RETRIES,
    SHOPPING_LIST_ADDITIONAL_ITEM_ID_ATTR,
    SHOPPING_LIST_ADDITIONAL_ITEM_ID_SUB_SELECTOR,
    SHOPPING_LIST_ADDITIONAL_ITEMS_SELECTOR,
    SHOPPING_LIST_CREATE_ADDITIONAL_ITEM_CONFIRM_SUB_SELECTOR,
    SHOPPING_LIST_CREATE_ADDITIONAL_ITEM_INPUT_SUB_SELECTOR,
    SHOPPING_LIST_CREATE_ADDITIONAL_ITEM_SELECTOR,
)
from cookidoo_api.exceptions import CookidooActionException, CookidooException
from cookidoo_api.types import CookidooConfig, CookidooItem

_LOGGER = logging.getLogger(__name__)


async def create_additional_items(
    cfg: CookidooConfig,
    page: Page,
    out_dir: str,
    additional_items: list[CookidooItem],
) -> list[CookidooItem]:
    """Update additional items.

    Parameters
    ----------
    cfg
        Cookidoo config
    page
        The page, which should have been validated already
    out_dir
        The directory to store output such as trace or screenshots
    additional_items
        The additional items to update, only the label can be set, as the default state `pending` is forced (chain with immediate update call for work-around)

    Returns
    -------
    list[CookidooItem]
        The list of the additional items

    Raises
    ------
    CookidooSelectorException
        When the page does not behave as expected and some content is not available
    CookidooActionException
        When the page does not allow to perform an expected action
    CookidooUnexpectedStateException
        When something should be changes such as the state, but it is already in that state

    """

    async def create_additional_item(i: int, additional_item: CookidooItem) -> None:
        """Create additional item."""
        _logger = _LOGGER.getChild(f"{i}")
        additional_item_sel = (
            f"{SHOPPING_LIST_ADDITIONAL_ITEMS_SELECTOR} .additional-items-list-item"
        )
        additional_item_count_before = len(
            await page.query_selector_all(additional_item_sel)
        )

        input_el = await selector(
            page,
            [
                SHOPPING_LIST_CREATE_ADDITIONAL_ITEM_SELECTOR,
                SHOPPING_LIST_CREATE_ADDITIONAL_ITEM_INPUT_SUB_SELECTOR,
            ],
        )

        _logger.debug(
            "Scroll to: %s",
            [
                SHOPPING_LIST_CREATE_ADDITIONAL_ITEM_SELECTOR,
                SHOPPING_LIST_CREATE_ADDITIONAL_ITEM_INPUT_SUB_SELECTOR,
            ],
        )
        await scroller(
            page,
            input_el,
            "Cannot scroll to new additional item input",
        )
        if cfg["screenshots"]:
            await page.screenshot(
                path=f"{out_dir}/2-{i}-1-before-additional-item-create.png"
            )

        _logger.debug(
            "Focus and enter value in input as '%s'",
            additional_item["label"],
        )
        try:
            await input_el.focus()
            await input_el.fill(additional_item["label"])
        except PlaywrightTimeoutError as e:
            raise CookidooActionException(
                f"Enter label into input field failed due to a timeout.\n{additional_item}"
            ) from e

        # Option 2: Clear by simulating Ctrl+A and Backspace (if you need to simulate user input)
        # page.click(input_selector)  # Ensures it's clicked
        # page.keyboard.press("Control+A")  # Select all text
        # page.keyboard.press("Backspace")  # Clear the field
        # page.keyboard.type(additional_item["label"])  # Enter the value

        if cfg["screenshots"]:
            await page.screenshot(
                path=f"{out_dir}/2-{i}-2-label-enter-value-additional-item.png"
            )

        _logger.debug("Get create confirm button")
        confirm_el = await selector(
            page,
            [
                SHOPPING_LIST_CREATE_ADDITIONAL_ITEM_SELECTOR,
                SHOPPING_LIST_CREATE_ADDITIONAL_ITEM_CONFIRM_SUB_SELECTOR,
            ],
        )
        _logger.debug("Click create confirm button")
        await clicker(
            page,
            confirm_el,
            f"Cannot click on create confirm button of additional item ({i}): {additional_item}",
        )
        # Await network stuff
        await page.wait_for_load_state(
            "networkidle"
        )  # Waits until there are no network connections for at least 500ms
        # # Hard-coded timeout for better behaviour after heavy network related actions
        # await page.wait_for_timeout(100)

        new_additional_item_sel = (
            f"{additional_item_sel}:nth-child({additional_item_count_before+1})"
        )
        await waiter(
            page,
            f"{additional_item_sel}:nth-child({additional_item_count_before+1})",  # Await for the n+1st item in the list, which should be the one we just added
            message="Additional item has not been added to pending additional items list",
        )
        new_additional_item_el = await selector(page, new_additional_item_sel)

        id_el = await selector(
            page,
            [new_additional_item_sel, SHOPPING_LIST_ADDITIONAL_ITEM_ID_SUB_SELECTOR],
        )
        id = await id_el.get_attribute(SHOPPING_LIST_ADDITIONAL_ITEM_ID_ATTR)
        if not id:
            raise CookidooException(
                f"The id of created additional item is empty:\n{await id_el.inner_html()}",
            )
        additional_item["id"] = id

        _logger.debug(
            "Scroll to: %s",
            additional_item,
        )
        await scroller(page, new_additional_item_el)

        if cfg["screenshots"]:
            await page.screenshot(
                path=f"{out_dir}/2-{i}-4-after-additional-item-create.png"
            )

        _logger.debug(
            "Create '%s' [%s]",
            additional_item["label"],
            additional_item["id"],
        )

    for i, additional_item in enumerate(additional_items):
        for retry in range(cfg.get("retries", DEFAULT_RETRIES)):
            try:
                await create_additional_item(i, additional_item)
                break
            except CookidooException as e:
                if retry < cfg.get("retries", DEFAULT_RETRIES):
                    _LOGGER.warning(
                        "Could not create additional item (%d) on try #%d due to error:\n%s",
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
                        f"Cannot create additional item ({i}) as the page did not behave as expected.\n{additional_item}"
                    ) from e
    return additional_items
