"""Cookidoo API helpers."""

import asyncio
import json
import logging
import os
from typing import cast

from cookidoo_api.types import (
    CookidooItem,
    CookidooLocalizationConfig,
    CookidooRecipe,
    IngredientJSON,
    RecipeJSON,
)

_LOGGER = logging.getLogger(__name__)

localization_file_path = os.path.join(os.path.dirname(__file__), "localization.json")


def cookidoo_recipe_from_json(
    recipe: RecipeJSON,
) -> CookidooRecipe:
    """Convert an ingredient received from the API to a cookidoo item."""
    return CookidooRecipe(
        id=recipe["id"],
        name=recipe["title"],
        ingredients=[
            cookidoo_item_from_ingredient(ingredient)
            for ingredient in recipe["recipeIngredientGroups"]
        ],
    )


def cookidoo_item_from_ingredient(
    ingredient: IngredientJSON,
) -> CookidooItem:
    """Convert an ingredient received from the API to a cookidoo item."""
    return CookidooItem(
        id=ingredient["id"],
        name=ingredient["ingredientNotation"],
        isOwned=ingredient["isOwned"],
        description=f"{ingredient['quantity']['value']} {ingredient['unitNotation']}"
        if ingredient["unitNotation"] and ingredient["quantity"]
        else str(ingredient["quantity"]["value"])
        if ingredient["quantity"]
        else "",
    )


def __get_localization_options(
    country: str | None = None,
    language: str | None = None,
) -> list[CookidooLocalizationConfig]:
    with open(localization_file_path, encoding="utf-8") as file:
        options = cast(list[CookidooLocalizationConfig], json.loads(file.read()))
        return list(
            filter(
                lambda option: (not country or option["country_code"] == country)
                and (not language or option["language"] == language),
                options,
            )
        )


async def get_localization_options(
    country: str | None = None,
    language: str | None = None,
) -> list[CookidooLocalizationConfig]:
    """Get a list of possible localization options."""
    return await asyncio.get_running_loop().run_in_executor(
        None, __get_localization_options, country, language
    )


async def get_country_options() -> list[str]:
    """Get a list of possible country options."""
    return list({option["country_code"] for option in await get_localization_options()})


async def get_language_options() -> list[str]:
    """Get a list of possible language options."""
    return list({option["language"] for option in await get_localization_options()})
