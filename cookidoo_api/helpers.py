"""Cookidoo API helpers."""

import asyncio
import json
import logging
import os
from typing import cast

from cookidoo_api.types import (
    AdditionalItemJSON,
    CookidooAdditionalItem,
    CookidooCategory,
    CookidooCollection,
    CookidooIngredient,
    CookidooIngredientItem,
    CookidooLocalizationConfig,
    CookidooRecipe,
    CookidooRecipeDetails,
    IngredientJSON,
    ItemJSON,
    RecipeDetailsJSON,
    RecipeJSON,
)

_LOGGER = logging.getLogger(__name__)

localization_file_path = os.path.join(os.path.dirname(__file__), "localization.json")


def cookidoo_recipe_from_json(
    recipe: RecipeJSON,
) -> CookidooRecipe:
    """Convert a recipe received from the API to a cookidoo recipe."""
    return CookidooRecipe(
        id=recipe["id"],
        name=recipe["title"],
        ingredients=[
            cookidoo_ingredient_item_from_json(ingredient)
            for ingredient in recipe["recipeIngredientGroups"]
        ],
    )


def cookidoo_recipe_details_from_json(
    recipe: RecipeDetailsJSON,
) -> CookidooRecipeDetails:
    """Convert an recipe details received from the API to a cookidoo recipe details."""
    return CookidooRecipeDetails(
        id=recipe["id"],
        name=recipe["title"],
        ingredients=[
            cookidoo_ingredient_from_json(ingredient)
            for ingredientGroup in recipe["recipeIngredientGroups"]
            for ingredient in ingredientGroup["recipeIngredients"]
        ],
        difficulty=recipe["difficulty"],
        notes=[
            additional_notes["content"]
            for additional_notes in recipe["additionalInformation"]
        ],
        categories=[
            CookidooCategory(
                id=category["id"], name=category["title"], notes=category["subtitle"]
            )
            for category in recipe["categories"]
        ],
        collections=[
            CookidooCollection(
                id=collection["id"],
                name=collection["title"],
                total_recipes=collection["recipesCount"]["value"],
            )
            for collection in recipe["inCollections"]
        ],
        utensils=[utensil["utensilNotation"] for utensil in recipe["recipeUtensils"]],
        serving_size=f"{recipe["servingSize"]['quantity']['value']} {recipe["servingSize"]["unitNotation"]}",
        active_time=next(
            time_["quantity"]["value"]
            for time_ in recipe["times"]
            if time_["type"] == "activeTime"
        ),
        total_time=next(
            time_["quantity"]["value"]
            for time_ in recipe["times"]
            if time_["type"] == "totalTime"
        ),
    )


def cookidoo_ingredient_from_json(
    ingredient: IngredientJSON,
) -> CookidooIngredient:
    """Convert an ingredient received from the API to a cookidoo ingredient."""
    return CookidooIngredient(
        id=ingredient["localId"],
        name=ingredient["ingredientNotation"],
        description=f"{ingredient['quantity']['value']} {ingredient['unitNotation']}"
        if ingredient["unitNotation"] and ingredient["quantity"]
        else str(ingredient["quantity"]["value"])
        if ingredient["quantity"]
        else "",
    )


def cookidoo_ingredient_item_from_json(
    item: ItemJSON,
) -> CookidooIngredientItem:
    """Convert an ingredient item received from the API to a cookidoo item."""
    return CookidooIngredientItem(
        id=item["id"],
        name=item["ingredientNotation"],
        is_owned=item["isOwned"],
        description=f"{item['quantity']['value']} {item['unitNotation']}"
        if item["unitNotation"] and item["quantity"]
        else str(item["quantity"]["value"])
        if item["quantity"]
        else "",
    )


def cookidoo_additional_item_from_json(
    item: AdditionalItemJSON,
) -> CookidooAdditionalItem:
    """Convert an additional item received from the API to a cookidoo item."""
    return CookidooAdditionalItem(
        id=item["id"],
        name=item["name"],
        is_owned=item["isOwned"],
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
