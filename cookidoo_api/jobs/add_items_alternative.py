"""Add items (alternative)."""

import logging

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from cookidoo_api.actions import (
    clicker,
    feedback_closer,
    scroller,
    selector,
    state_waiter,
    waiter,
)
from cookidoo_api.const import (
    DEFAULT_RETRIES,
    RECIPE_SEARCH_ADD_OPTION_SHOPPING_LIST_SELECTOR,
    RECIPE_SEARCH_ADD_OPTIONS_SELECTOR,
    RECIPE_SEARCH_URL_TEMPLATE,
)
from cookidoo_api.exceptions import CookidooException, CookidooNavigationException
from cookidoo_api.helpers import error_message_selector
from cookidoo_api.types import CookidooConfig

_LOGGER = logging.getLogger(__name__)


async def add_items_alternative(
    cfg: CookidooConfig,
    page: Page,
    recipe_name: str,
    out_dir: str,
) -> None:
    """Add items to list from recipe.

    This is an alternative implementation which works also for free account, as on the recipe page the "Add to Shopping List" is not available for free accounts.

    Parameters
    ----------
    cfg
        Cookidoo config
    page
        The page, which should have been validated already
    recipe_name
        The name for the search bar of the recipe to add the items to the shopping list. Careful, this first element which be selected automatically.
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
                _LOGGER.debug(
                    "Go to recipe page: %s",
                    RECIPE_SEARCH_URL_TEMPLATE.format(recipe_name),
                )
                await page.goto(RECIPE_SEARCH_URL_TEMPLATE.format(recipe_name))
                await feedback_closer(page)

                _LOGGER.debug(
                    "Wait for add options to be visible/attached: %s",
                    RECIPE_SEARCH_ADD_OPTIONS_SELECTOR,
                )
                await page.wait_for_selector(RECIPE_SEARCH_ADD_OPTIONS_SELECTOR)
            except PlaywrightTimeoutError as e:
                raise CookidooNavigationException(
                    f"Recipe not found in search not found, due to timeout.\n{error_message_selector(page.url, RECIPE_SEARCH_ADD_OPTIONS_SELECTOR)}"
                ) from e

            if cfg["screenshots"]:
                await page.screenshot(path=f"{out_dir}/1-recipe.png")

            _LOGGER.debug(
                "Extract the options button: %s",
                RECIPE_SEARCH_ADD_OPTIONS_SELECTOR,
            )
            await waiter(page, RECIPE_SEARCH_ADD_OPTIONS_SELECTOR)
            options_el = await selector(page, RECIPE_SEARCH_ADD_OPTIONS_SELECTOR)
            await scroller(page, options_el)

            if cfg["screenshots"]:
                await page.screenshot(path=f"{out_dir}/2-recipe-add-options.png")

            _LOGGER.debug(
                "Click on options button: %s",
                RECIPE_SEARCH_ADD_OPTIONS_SELECTOR,
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
                RECIPE_SEARCH_ADD_OPTION_SHOPPING_LIST_SELECTOR,
            )
            await waiter(page, RECIPE_SEARCH_ADD_OPTION_SHOPPING_LIST_SELECTOR)
            shopping_list_option_el = await selector(
                page, RECIPE_SEARCH_ADD_OPTION_SHOPPING_LIST_SELECTOR
            )

            await scroller(page, shopping_list_option_el)

            _LOGGER.debug(
                "Click on shopping list option button: %s",
                RECIPE_SEARCH_ADD_OPTION_SHOPPING_LIST_SELECTOR,
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

            await state_waiter(
                page, RECIPE_SEARCH_ADD_OPTION_SHOPPING_LIST_SELECTOR, "hidden"
            )

            if cfg["screenshots"]:
                await page.screenshot(path=f"{out_dir}/4-recipe-items-added.png")
            break
        except CookidooException as e:
            if retry < cfg.get("retries", DEFAULT_RETRIES):
                _LOGGER.warning(
                    "Could not add items of recipe (%s) on try #%d due to error:\n%s",
                    recipe_name,
                    retry,
                    e,
                )
            else:
                _LOGGER.warning(
                    "Exhausted all #%d retries for add items (%s)",
                    retry + 1,
                    recipe_name,
                )
                raise CookidooException(
                    f"Could not add items of recipe ({recipe_name})"
                ) from e
