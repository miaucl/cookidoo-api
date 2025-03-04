"""Cookidoo API helpers."""

import json
import logging
import os
from typing import cast

import aiofiles

from cookidoo_api.raw_types import (
    AdditionalItemJSON,
    AuthResponseJSON,
    CalendarDayJSON,
    CustomCollectionJSON,
    IngredientJSON,
    ItemJSON,
    ManagedCollectionJSON,
    QuantityJSON,
    RecipeDetailsJSON,
    RecipeJSON,
    SubscriptionJSON,
    UserInfoJSON,
)
from cookidoo_api.types import (
    CookidooAdditionalItem,
    CookidooAuthResponse,
    CookidooCalendarDay,
    CookidooCalendarDayRecipe,
    CookidooCategory,
    CookidooChapter,
    CookidooChapterRecipe,
    CookidooCollection,
    CookidooIngredient,
    CookidooIngredientItem,
    CookidooLocalizationConfig,
    CookidooRecipeCollection,
    CookidooShoppingRecipe,
    CookidooShoppingRecipeDetails,
    CookidooSubscription,
    CookidooUserInfo,
)

_LOGGER = logging.getLogger(__name__)

localization_file_path = os.path.join(os.path.dirname(__file__), "localization.json")


def cookidoo_auth_data_from_json(
    auth_data: AuthResponseJSON,
) -> CookidooAuthResponse:
    """Convert a auth data received from the API to a cookidoo auth data."""
    return CookidooAuthResponse(
        sub=auth_data["sub"],
        access_token=auth_data["access_token"],
        refresh_token=auth_data["refresh_token"],
        token_type=auth_data["token_type"],
        expires_in=auth_data["expires_in"],
    )


def cookidoo_user_info_from_json(
    user_info: UserInfoJSON,
) -> CookidooUserInfo:
    """Convert a user info received from the API to a cookidoo user info."""
    return CookidooUserInfo(
        username=user_info["username"],
        description=user_info.get("description"),
        picture=user_info["picture"],
    )


def cookidoo_subscription_from_json(
    subscription: SubscriptionJSON,
) -> CookidooSubscription:
    """Convert a subscription received from the API to a cookidoo subscription."""
    return CookidooSubscription(
        active=subscription["active"],
        expires=subscription["expires"],
        start_date=subscription["startDate"],
        status=subscription["status"],
        subscription_level=subscription["subscriptionLevel"],
        subscription_source=subscription["subscriptionSource"],
        type=subscription["type"],
        extended_type=subscription["extendedType"],
    )


def cookidoo_collection_from_json(
    collection: CustomCollectionJSON | ManagedCollectionJSON,
) -> CookidooCollection:
    """Convert a collection received from the API to a cookidoo collection."""
    return CookidooCollection(
        id=collection["id"],
        name=collection["title"],
        description=cast(str, collection.get("description", None)),
        chapters=[
            CookidooChapter(
                name=chapter["title"],
                recipes=[
                    CookidooChapterRecipe(
                        id=recipe["id"],
                        name=recipe["title"],
                        total_time=int(float(recipe["totalTime"])),
                    )
                    for recipe in chapter["recipes"]
                ],
            )
            for chapter in collection["chapters"]
        ],
    )


def cookidoo_recipe_from_json(
    recipe: RecipeJSON,
) -> CookidooShoppingRecipe:
    """Convert a shopping recipe received from the API to a cookidoo shopping recipe."""
    return CookidooShoppingRecipe(
        id=recipe["id"],
        name=recipe["title"],
        ingredients=[
            cookidoo_ingredient_from_json(ingredient)
            for ingredient in recipe["recipeIngredientGroups"]
        ],
    )


def cookidoo_quantity_from_json(
    quantity: QuantityJSON,
) -> str:
    """Convert an quantity received from the API to a str."""
    if "value" in quantity and quantity["value"]:
        return str(quantity["value"])
    elif (
        "from" in quantity and "to" in quantity and quantity["from"] and quantity["to"]
    ):
        return f"{quantity['from']} - {quantity['to']}"
    else:
        return ""


def cookidoo_recipe_details_from_json(
    recipe: RecipeDetailsJSON,
) -> CookidooShoppingRecipeDetails:
    """Convert an recipe details received from the API to a cookidoo recipe details."""
    return CookidooShoppingRecipeDetails(
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
            CookidooRecipeCollection(
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
            if time_["type"] == "activeTime" and time_["quantity"]["value"]
        ),
        total_time=next(
            time_["quantity"]["value"]
            for time_ in recipe["times"]
            if time_["type"] == "totalTime" and time_["quantity"]["value"]
        ),
    )


def cookidoo_ingredient_from_json(
    ingredient: IngredientJSON | ItemJSON,
) -> CookidooIngredient:
    """Convert an ingredient received from the API to a cookidoo ingredient."""
    return CookidooIngredient(
        id=ingredient["localId"] if "localId" in ingredient else ingredient["id"],  # type: ignore[typeddict-item]
        name=ingredient["ingredientNotation"],
        description=f"{cookidoo_quantity_from_json(ingredient['quantity'])} {ingredient['unitNotation']}"
        if ingredient["unitNotation"] and ingredient["quantity"]
        else cookidoo_quantity_from_json(ingredient["quantity"])
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
        description=f"{cookidoo_quantity_from_json(item['quantity'])} {item['unitNotation']}"
        if item["unitNotation"] and item["quantity"]
        else str(cookidoo_quantity_from_json(item["quantity"]))
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


def cookidoo_calendar_day_from_json(
    calendar_day: CalendarDayJSON,
) -> CookidooCalendarDay:
    """Convert a calendar day received from the API to a cookidoo item."""
    return CookidooCalendarDay(
        id=calendar_day["id"],
        title=calendar_day["title"],
        recipes=[
            CookidooCalendarDayRecipe(
                id=recipe["id"], name=recipe["title"], total_time=recipe["totalTime"]
            )
            for recipe in calendar_day["recipes"]
        ],
    )


async def __get_localization_options(
    country: str | None = None,
    language: str | None = None,
) -> list[CookidooLocalizationConfig]:
    async with aiofiles.open(localization_file_path, encoding="utf-8") as file:
        options_ = cast(list[dict[str, str]], json.loads(await file.read()))
        options = (CookidooLocalizationConfig(**x) for x in options_)
        filtered_options = filter(
            lambda option: (not country or option.country_code == country)
            and (not language or option.language == language),
            options,
        )
        return list(cast(list[CookidooLocalizationConfig], filtered_options))


async def get_localization_options(
    country: str | None = None,
    language: str | None = None,
) -> list[CookidooLocalizationConfig]:
    """Get a list of possible localization options."""
    return await __get_localization_options(country, language)


async def get_country_options() -> list[str]:
    """Get a list of possible country options."""
    return list({option.country_code for option in await get_localization_options()})


async def get_language_options() -> list[str]:
    """Get a list of possible language options."""
    return list({option.language for option in await get_localization_options()})
