"""Remove items."""

import logging

from playwright.async_api import Page

from cookidoo_api.actions import clicker, scroller, selector, state_waiter, waiter
from cookidoo_api.const import (
    DEFAULT_RETRIES,
    SHOPPING_LIST_RECIPE_OPTIONS_SELECTOR_TEMPLATE,
    SHOPPING_LIST_RECIPE_REMOVE_OPTION_SELECTOR_TEMPLATE,
    SHOPPING_LIST_RECIPES_TAB_SELECTOR,
)
from cookidoo_api.exceptions import CookidooException
from cookidoo_api.types import CookidooConfig

_LOGGER = logging.getLogger(__name__)


async def remove_items(
    cfg: CookidooConfig,
    page: Page,
    recipe_id: str,
    out_dir: str,
) -> None:
    """Remove items from list of recipe.

    Parameters
    ----------
    cfg
        Cookidoo config
    page
        The page, which should have been validated already
    recipe_id
        The id of the recipe to remove the items from the shopping list
    out_dir
        The directory to store output such as trace or screenshots

    Raises
    ------
    CookidooSelectorException
        When the page does not behave as expected and some content is not available
    CookidooActionException
        When the page does not allow to perform an expected action

    """
    for retry in range(cfg.get("retries", DEFAULT_RETRIES)):
        try:
            if cfg["screenshots"]:
                await page.screenshot(path=f"{out_dir}/1-shopping-list.png")

            _LOGGER.debug(
                "Extract the recipe tab: %s",
                SHOPPING_LIST_RECIPES_TAB_SELECTOR,
            )
            await waiter(page, SHOPPING_LIST_RECIPES_TAB_SELECTOR)
            recipe_tab_el = await selector(page, SHOPPING_LIST_RECIPES_TAB_SELECTOR)
            _LOGGER.debug(
                "Click on recipe tab: %s",
                SHOPPING_LIST_RECIPES_TAB_SELECTOR,
            )
            await clicker(
                page,
                recipe_tab_el,
                "Cannot click on recipe tab",
            )

            if cfg["screenshots"]:
                await page.screenshot(path=f"{out_dir}/2-shopping-list-recipes.png")

            _LOGGER.debug(
                "Extract the options button: %s",
                SHOPPING_LIST_RECIPE_OPTIONS_SELECTOR_TEMPLATE.format(recipe_id),
            )
            await waiter(
                page, SHOPPING_LIST_RECIPE_OPTIONS_SELECTOR_TEMPLATE.format(recipe_id)
            )
            options_el = await selector(
                page, SHOPPING_LIST_RECIPE_OPTIONS_SELECTOR_TEMPLATE.format(recipe_id)
            )
            await scroller(page, options_el)

            if cfg["screenshots"]:
                await page.screenshot(path=f"{out_dir}/3-recipe-options.png")

            _LOGGER.debug(
                "Click on options button: %s",
                SHOPPING_LIST_RECIPE_OPTIONS_SELECTOR_TEMPLATE.format(recipe_id),
            )
            await clicker(
                page,
                options_el,
                "Cannot click on options button of recipe",
            )

            if cfg["screenshots"]:
                await page.screenshot(path=f"{out_dir}/4-recipe-options-dropdown.png")

            _LOGGER.debug(
                "Extract the remove option button: %s",
                SHOPPING_LIST_RECIPE_REMOVE_OPTION_SELECTOR_TEMPLATE.format(recipe_id),
            )
            await waiter(
                page,
                SHOPPING_LIST_RECIPE_REMOVE_OPTION_SELECTOR_TEMPLATE.format(recipe_id),
            )
            remove_option_el = await selector(
                page,
                SHOPPING_LIST_RECIPE_REMOVE_OPTION_SELECTOR_TEMPLATE.format(recipe_id),
            )

            _LOGGER.debug(
                "Click on remove option button: %s",
                SHOPPING_LIST_RECIPE_REMOVE_OPTION_SELECTOR_TEMPLATE.format(recipe_id),
            )
            await clicker(
                page,
                remove_option_el,
                "Cannot click on remove option button of recipe",
            )

            # Await network stuff
            await page.wait_for_load_state(
                "networkidle"
            )  # Waits until there are no network connections for at least 500ms

            await state_waiter(
                page,
                SHOPPING_LIST_RECIPE_OPTIONS_SELECTOR_TEMPLATE.format(recipe_id),
                "detached",
            )

            if cfg["screenshots"]:
                await page.screenshot(path=f"{out_dir}/5-recipe-items-removed.png")

            break
        except CookidooException as e:
            if retry < cfg.get("retries", DEFAULT_RETRIES):
                _LOGGER.warning(
                    "Could not remove items of recipe (%s) on try #%d due to error:\n%s",
                    recipe_id,
                    retry,
                    e,
                )
            else:
                _LOGGER.warning(
                    "Exhausted all #%d retries for remove items (%s)",
                    retry + 1,
                    recipe_id,
                )
                raise CookidooException(
                    f"Could not remove items of recipe ({recipe_id})"
                ) from e
