"""Update additional items."""

import logging

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from cookidoo_api.actions import (
    clicker,
    hoverer,
    scroller,
    selector,
    state_waiter,
    waiter,
)
from cookidoo_api.const import (
    DEFAULT_RETRIES,
    DOM_CHECK_ATTACHED,
    SHOPPING_LIST_ADDITIONAL_CHECKBOX_SUB_SELECTOR,
    SHOPPING_LIST_ADDITIONAL_CHECKED_ITEMS_SELECTOR,
    SHOPPING_LIST_ADDITIONAL_ITEM_EDIT_SUB_SELECTOR,
    SHOPPING_LIST_ADDITIONAL_ITEM_HOVER_SUB_SELECTOR,
    SHOPPING_LIST_ADDITIONAL_ITEM_LABEL_SUB_SELECTOR,
    SHOPPING_LIST_ADDITIONAL_ITEMS_SELECTOR,
    SHOPPING_LIST_EDIT_ADDITIONAL_ITEM_CONFIRM_SUB_SELECTOR,
    SHOPPING_LIST_EDIT_ADDITIONAL_ITEM_INPUT_SUB_SELECTOR,
    SHOPPING_LIST_EDIT_ADDITIONAL_ITEM_SELECTOR,
)
from cookidoo_api.exceptions import CookidooActionException, CookidooException
from cookidoo_api.types import CookidooConfig, CookidooItem

_LOGGER = logging.getLogger(__name__)


async def update_additional_items(
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
        The additional items to update, only the state and label can be changed

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

    async def update_additional_item(i: int, additional_item: CookidooItem) -> None:
        """Update additional item."""
        _logger = _LOGGER.getChild(f"{i}")
        pending_sel = f'{SHOPPING_LIST_ADDITIONAL_ITEMS_SELECTOR} .additional-items-list-item:has(label[id="{additional_item["id"]}"])'
        checked_sel = f'{SHOPPING_LIST_ADDITIONAL_CHECKED_ITEMS_SELECTOR} .additional-items-list-item:has(label[id="{additional_item["id"]}"])'
        additional_item_sel = f"{pending_sel},{checked_sel}"

        _logger.debug(
            "Extract pending/checked checkbox: %s | %s",
            pending_sel,
            checked_sel,
        )
        pending_el = await page.query_selector(pending_sel)  # Can be None
        checked_el = await page.query_selector(checked_sel)  # Can be None
        additional_item_el = await selector(
            page,
            additional_item_sel,
            f"Additional item ({i}) {additional_item['id']} not found in either list.",
        )

        # Assert still attached to DOM
        if not await additional_item_el.evaluate(DOM_CHECK_ATTACHED):
            raise CookidooActionException(
                f"Cannot interact with additional item ({i}) as it has been detached from the DOM.\n{additional_item}"
            )

        _logger.debug(
            "Scroll to: %s | %s",
            pending_sel,
            checked_sel,
        )
        await scroller(
            page,
            additional_item_el,
            f"Cannot scroll to additional item ({i}): {additional_item}",
        )
        if cfg["screenshots"]:
            await page.screenshot(
                path=f"{out_dir}/2-{i}-1-before-additional-item-update.png"
            )

        # Handle label update
        _logger.debug("Extract current label")
        label_text_el = await selector(
            page,
            [additional_item_sel, SHOPPING_LIST_ADDITIONAL_ITEM_LABEL_SUB_SELECTOR],
            f"Label of additional item ({i}) {additional_item['id']} not found.",
        )
        if await label_text_el.text_content() != additional_item["label"]:
            _logger.debug(
                "Update label: %s | %s",
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
                f"Cannot hover over additional item ({i}): {additional_item}",
            )

            if cfg["screenshots"]:
                await page.screenshot(
                    path=f"{out_dir}/2-{i}-2.1-hover-additional-item.png"
                )

            _logger.debug("Get edit button")
            edit_el = await selector(
                page,
                [additional_item_sel, SHOPPING_LIST_ADDITIONAL_ITEM_EDIT_SUB_SELECTOR],
            )
            _logger.debug(
                "Click on edit button: %s",
                SHOPPING_LIST_ADDITIONAL_ITEM_EDIT_SUB_SELECTOR,
            )
            await clicker(
                page,
                edit_el,
                f"Cannot click on edit button of additional item ({i}): {additional_item}",
            )
            await waiter(
                page,
                SHOPPING_LIST_EDIT_ADDITIONAL_ITEM_SELECTOR,
                message="Item did not become visible",
            )

            if cfg["screenshots"]:
                await page.screenshot(
                    path=f"{out_dir}/2-{i}-2.2-label-edit-additional-item.png"
                )

            _logger.debug("Focus label input")
            input_el = await selector(
                page,
                [
                    SHOPPING_LIST_EDIT_ADDITIONAL_ITEM_SELECTOR,
                    SHOPPING_LIST_EDIT_ADDITIONAL_ITEM_INPUT_SUB_SELECTOR,
                ],
            )

            _logger.debug(
                "Focus and update value in input to '%s': %s",
                additional_item["label"],
                SHOPPING_LIST_ADDITIONAL_ITEM_EDIT_SUB_SELECTOR,
            )
            try:
                await input_el.focus()
                await input_el.fill(additional_item["label"])
            except PlaywrightTimeoutError as e:
                raise CookidooActionException(
                    f"Update of label via input field failed due to a timeout.\n{additional_item}"
                ) from e

            # Option 2: Clear by simulating Ctrl+A and Backspace (if you need to simulate user input)
            # page.click(input_selector)  # Ensures it's clicked
            # page.keyboard.press("Control+A")  # Select all text
            # page.keyboard.press("Backspace")  # Clear the field
            # page.keyboard.type(additional_item["label"])  # Enter the value

            if cfg["screenshots"]:
                await page.screenshot(
                    path=f"{out_dir}/2-{i}-2.3-label-enter-value-additional-item.png"
                )

            _logger.debug("Get edit confirm button")
            confirm_el = await selector(
                page,
                [
                    SHOPPING_LIST_EDIT_ADDITIONAL_ITEM_SELECTOR,
                    SHOPPING_LIST_EDIT_ADDITIONAL_ITEM_CONFIRM_SUB_SELECTOR,
                ],
            )
            await clicker(
                page,
                confirm_el,
                f"Cannot click on edit confirm button of additional item ({i}): {additional_item}",
            )
            # Hard-coded timeout for better behaviour after heavy network related actions
            await page.wait_for_timeout(100)
            # Await network stuff
            await page.wait_for_load_state(
                "networkidle"
            )  # Waits until there are no network connections for at least 500ms
            await state_waiter(
                page,
                SHOPPING_LIST_EDIT_ADDITIONAL_ITEM_SELECTOR,
                state="hidden",
                message="Additional item editor did not become hidden",
            )
            await waiter(
                page,
                additional_item_sel,
                message="Additional item did not become visible",
            )

            if cfg["screenshots"]:
                await page.screenshot(
                    path=f"{out_dir}/2-{i}-2.4-label-edited-additional-item.png"
                )

        # Handle state update
        if (
            pending_el
            and additional_item["state"] == "checked"
            or checked_el
            and additional_item["state"] == "pending"
        ):
            additional_item_target_sel = (
                pending_sel if additional_item["state"] == "pending" else checked_sel
            )
            _logger.debug(
                "Update state: %s | %s",
                pending_sel,
                checked_sel,
            )

            checkbox_from_el = await selector(
                page,
                [
                    additional_item_sel,
                    SHOPPING_LIST_ADDITIONAL_CHECKBOX_SUB_SELECTOR,
                ],
            )

            if cfg["screenshots"]:
                await page.screenshot(
                    path=f"{out_dir}/2-{i}-3.1-before-additional-item-state-update.png"
                )

            # Toggle the element
            _logger.debug(
                "Click on checkbox and set to '%s': %s | %s",
                additional_item["state"],
                pending_sel,
                checked_sel,
            )
            await clicker(
                page,
                checkbox_from_el,
                f"Cannot click on checkbox of of additional item ({i}): {additional_item}",
            )
            # Await network stuff
            await page.wait_for_load_state(
                "networkidle"
            )  # Waits until there are no network connections for at least 500ms
            # # Hard-coded timeout for better behaviour after heavy network related actions
            # await page.wait_for_timeout(100)

            # Await the to item
            _logger.debug(
                "Wait to be attached in the new list: %s",
                additional_item_target_sel,
            )
            checkbox_to_el = await waiter(
                page,
                [
                    additional_item_target_sel,
                    SHOPPING_LIST_ADDITIONAL_CHECKBOX_SUB_SELECTOR,
                ],
                message=f"Updated additional item ({i}) not found due to timeout: {str(additional_item)}\nIt should now be in state '{additional_item["state"]}' and in its respective list.",
            )

            _logger.debug(
                "Scroll to: %s",
                additional_item_sel,
            )
            await scroller(
                page,
                checkbox_to_el,
                f"Cannot scroll to checkbox of additional item ({i}): {additional_item}",
            )
            if cfg["screenshots"]:
                await page.screenshot(
                    path=f"{out_dir}/2-{i}-3.2-after-additional-item-state-update.png"
                )

        if cfg["screenshots"]:
            await page.screenshot(
                path=f"{out_dir}/2-{i}-4-after-additional-item-update.png"
            )

        _logger.debug(
            "Set '%s' [%s] state to: %s",
            additional_item["label"],
            additional_item["id"],
            additional_item["state"],
        )

    for i, additional_item in enumerate(additional_items):
        for retry in range(cfg.get("retries", DEFAULT_RETRIES)):
            try:
                await update_additional_item(i, additional_item)
                break
            except CookidooException as e:
                if retry < cfg.get("retries", DEFAULT_RETRIES):
                    _LOGGER.warning(
                        "Could not update additional item (%d) on try #%d due to error:\n%s",
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
                        f"Cannot update additional item ({i}) as the page did not behave as expected.\n{additional_item}"
                    ) from e
    return additional_items
