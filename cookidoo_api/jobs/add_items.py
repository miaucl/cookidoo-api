"""Add items."""

import logging

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from cookidoo_api.actions import clicker, scroller, selector, waiter
from cookidoo_api.const import (
    DEFAULT_RETRIES,
    RECIPE_ADD_OPTION_SHOPPING_LIST_SELECTOR,
    RECIPE_ADD_OPTIONS_SELECTOR_TEMPLATE,
    RECIPE_ADD_TO_SHOPPING_LIST_CONFIRM_SELECTOR,
    RECIPE_URL_PREFIX,
)
from cookidoo_api.exceptions import CookidooException, CookidooNavigationException
from cookidoo_api.helpers import error_message_selector
from cookidoo_api.types import CookidooConfig

_LOGGER = logging.getLogger(__name__)


async def add_items(
    cfg: CookidooConfig,
    page: Page,
    recipe_id: str,
    out_dir: str,
) -> None:
    """Add items to list from recipe.

    Parameters
    ----------
    cfg
        Cookidoo config
    page
        The page, which should have been validated already
    recipe_id
        The id of the recipe to add the items to the shopping list
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
                # Go to recipe page
                _LOGGER.debug("Go to recipe page: %s%s", RECIPE_URL_PREFIX, recipe_id)
                await page.goto(f"{RECIPE_URL_PREFIX}{recipe_id}")

                _LOGGER.debug(
                    "Wait for add options to be visible/attached: %s",
                    RECIPE_ADD_OPTIONS_SELECTOR_TEMPLATE.format(recipe_id),
                )
                await page.wait_for_selector(
                    RECIPE_ADD_OPTIONS_SELECTOR_TEMPLATE.format(recipe_id)
                )
            except PlaywrightTimeoutError as e:
                raise CookidooNavigationException(
                    f"Recipe page not found, due to timeout.\n{error_message_selector(page.url, RECIPE_ADD_OPTIONS_SELECTOR_TEMPLATE.format(recipe_id))}"
                ) from e

            if cfg["screenshots"]:
                await page.screenshot(path=f"{out_dir}/1-recipe.png")

            _LOGGER.debug(
                "Extract the options button: %s",
                RECIPE_ADD_OPTIONS_SELECTOR_TEMPLATE.format(recipe_id),
            )
            await waiter(page, RECIPE_ADD_OPTIONS_SELECTOR_TEMPLATE.format(recipe_id))
            options_el = await selector(
                page, RECIPE_ADD_OPTIONS_SELECTOR_TEMPLATE.format(recipe_id)
            )
            await scroller(page, options_el)

            if cfg["screenshots"]:
                await page.screenshot(path=f"{out_dir}/2-recipe-add-options.png")

            _LOGGER.debug(
                "Click on options button: %s",
                RECIPE_ADD_OPTIONS_SELECTOR_TEMPLATE.format(recipe_id),
            )
            await clicker(
                page,
                options_el,
                "Cannot click on add options button of recipe",
            )

            if cfg["screenshots"]:
                await page.screenshot(
                    path=f"{out_dir}/3-recipe-add-options-dropdown.png"
                )

            _LOGGER.debug(
                "Extract the shopping list option button: %s",
                RECIPE_ADD_OPTION_SHOPPING_LIST_SELECTOR,
            )
            await waiter(page, RECIPE_ADD_OPTION_SHOPPING_LIST_SELECTOR)
            shopping_list_option_el = await selector(
                page, RECIPE_ADD_OPTION_SHOPPING_LIST_SELECTOR
            )

            _LOGGER.debug(
                "Click on shopping list option button: %s",
                RECIPE_ADD_OPTION_SHOPPING_LIST_SELECTOR,
            )
            await clicker(
                page,
                shopping_list_option_el,
                "Cannot click on shopping list option button of recipe",
            )

            # Await network stuff
            await page.wait_for_load_state(
                "networkidle"
            )  # Waits until there are no network connections for at least 500ms

            await waiter(page, RECIPE_ADD_TO_SHOPPING_LIST_CONFIRM_SELECTOR)

            if cfg["screenshots"]:
                await page.screenshot(path=f"{out_dir}/4-recipe-items-added.png")
            break
        except CookidooException as e:
            if retry < cfg.get("retries", DEFAULT_RETRIES):
                _LOGGER.warning(
                    "Could not add items of recipe (%s) on try #%d due to error:\n%s",
                    recipe_id,
                    retry,
                    e,
                )
            else:
                _LOGGER.warning(
                    "Exhausted all #%d retries for add items (%s)",
                    retry + 1,
                    recipe_id,
                )
                raise CookidooException(
                    f"Could not add items of recipe ({recipe_id})"
                ) from e
