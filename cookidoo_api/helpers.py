"""Cookidoo API helpers."""

import json
import logging
import os
from typing import cast
from urllib.parse import urlparse

import aiofiles
import isodate

from cookidoo_api.raw_types import (
    AdditionalItemJSON,
    AuthResponseJSON,
    CalendarDayJSON,
    CalenderDayRecipeJSON,
    CreateCustomRecipeRequestJSON,
    CustomCollectionJSON,
    CustomRecipeJSON,
    CustomRecipesResponseJSON,
    DescriptiveAssetJSON,
    EditCustomRecipeRequestJSON,
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
    CookidooCreateCustomRecipe,
    CookidooCustomRecipe,
    CookidooEditCustomRecipe,
    CookidooIngredient,
    CookidooIngredientItem,
    CookidooInstruction,
    CookidooLocalizationConfig,
    CookidooNutrition,
    CookidooNutritionGroup,
    CookidooRecipeCollection,
    CookidooRecipeNutrition,
    CookidooShoppingRecipe,
    CookidooShoppingRecipeDetails,
    CookidooStepSettings,
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


def _process_image_url(url: str) -> tuple[str, str]:
    """Process image URL by replacing transformation placeholders.

    Returns
    -------
    tuple[str, str]
        A tuple of (thumbnail_url, image_url) where:
        - thumbnail_url uses t_web_shared_recipe_221x240 transformation
        - image_url uses t_web_rdp_recipe_584x480_1_5x transformation

    """
    thumbnail = url.replace("{transformation}", "t_web_shared_recipe_221x240")
    image = url.replace("{transformation}", "t_web_rdp_recipe_584x480_1_5x")
    return thumbnail, image


def _extract_images_from_descriptive_assets(
    descriptive_assets: list[DescriptiveAssetJSON],
) -> tuple[str | None, str | None]:
    """Extract thumbnail and image URLs from descriptive assets.

    Returns
    -------
    tuple[str | None, str | None]
        A tuple of (thumbnail_url, image_url) extracted from the first
        available image URL in descriptive assets.

    """
    thumbnail: str | None = None
    image: str | None = None

    # Get the first available image URL from any variant
    for asset in descriptive_assets:
        _LOGGER.debug(asset)
        for variant, url in asset.items():
            _LOGGER.debug(variant)
            if url and variant in ("square", "portrait", "landscape"):
                thumbnail, image = _process_image_url(str(url))
                break
        if thumbnail:
            break

    return thumbnail, image


def _construct_recipe_url(
    localization: CookidooLocalizationConfig | None,
    recipe_id: str,
    path_prefix: str = "recipes/recipe",
) -> str:
    """Construct a recipe URL from localization config and recipe ID.

    Parameters
    ----------
    localization
        The localization config containing the domain and language.
    recipe_id
        The recipe ID to use in the URL.
    path_prefix
        The path prefix for the recipe URL. Defaults to "recipes/recipe".

    Returns
    -------
    str
        The constructed recipe URL, or empty string if localization is None.

    """
    if not localization:
        return ""

    parsed_url = urlparse(localization.url)
    domain = parsed_url.netloc
    return f"https://{domain}/{path_prefix}/{localization.language}/{recipe_id}"


def cookidoo_recipe_from_json(
    recipe: RecipeJSON,
    localization: CookidooLocalizationConfig | None = None,
) -> CookidooShoppingRecipe:
    """Convert a shopping recipe received from the API to a cookidoo shopping recipe."""
    thumbnail, image = None, None
    descriptive_assets = recipe.get("descriptiveAssets")
    if descriptive_assets is not None:
        thumbnail, image = _extract_images_from_descriptive_assets(descriptive_assets)
    url = _construct_recipe_url(localization, recipe["id"])

    return CookidooShoppingRecipe(
        id=recipe["id"],
        name=recipe["title"],
        ingredients=[
            cookidoo_ingredient_from_json(ingredient)
            for ingredient in recipe["recipeIngredientGroups"]
        ],
        thumbnail=thumbnail,
        image=image,
        url=url,
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
    localization: CookidooLocalizationConfig | None = None,
) -> CookidooShoppingRecipeDetails:
    """Convert an recipe details received from the API to a cookidoo recipe details."""
    thumbnail, image = None, None
    descriptive_assets = recipe.get("descriptiveAssets")
    if descriptive_assets is not None:
        thumbnail, image = _extract_images_from_descriptive_assets(descriptive_assets)
    url = _construct_recipe_url(localization, recipe["id"])

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
        serving_size=recipe["servingSize"]["quantity"]["value"] or 0,
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
        nutrition_groups=[
            CookidooNutritionGroup(
                name=ng["name"],
                recipe_nutritions=[
                    CookidooRecipeNutrition(
                        nutritions=[
                            CookidooNutrition(
                                number=n["number"],
                                type=n["type"],
                                unittype=n["unittype"],
                            )
                            for n in rn["nutritions"]
                        ],
                        quantity=rn["quantity"],
                        unit_notation=rn["unitNotation"],
                    )
                    for rn in ng["recipeNutritions"]
                ],
            )
            for ng in recipe.get("nutritionGroups", [])
        ],
        thumbnail=thumbnail,
        image=image,
        url=url,
    )


def cookidoo_custom_recipe_from_json(
    recipe: CustomRecipeJSON,
    localization: CookidooLocalizationConfig | None = None,
) -> CookidooCustomRecipe:
    """Convert a custom recipe received from the API to a cookidoo custom recipe."""
    recipe_content = recipe["recipeContent"]

    total_time_raw = recipe_content.get("totalTime")
    active_time_raw = recipe_content.get("prepTime")
    total_time = (
        int(isodate.parse_duration(total_time_raw).total_seconds())
        if total_time_raw
        else 0
    )
    active_time = (
        int(isodate.parse_duration(active_time_raw).total_seconds())
        if active_time_raw
        else 0
    )

    thumbnail: str | None = None
    image: str | None = None

    image = recipe_content.get("image", None)
    if image:
        thumbnail, image = _process_image_url(image)

    url = _construct_recipe_url(localization, recipe["recipeId"], "created-recipes")

    recipe_yield = recipe_content.get("recipeYield")
    serving_size = recipe_yield["value"] if recipe_yield else 0

    return CookidooCustomRecipe(
        id=recipe["recipeId"],
        name=recipe_content["name"],
        ingredients=recipe_content.get("recipeIngredient", []),
        instructions=recipe_content.get("recipeInstructions", []),
        serving_size=serving_size,
        total_time=total_time,
        active_time=active_time,
        tools=recipe_content.get("tool", []),
        thumbnail=thumbnail,
        image=image,
        url=url,
    )


def cookidoo_ingredient_from_json(
    ingredient: IngredientJSON | ItemJSON,
) -> CookidooIngredient:
    """Convert an ingredient received from the API to a cookidoo ingredient."""
    return CookidooIngredient(
        id=ingredient["localId"] if "localId" in ingredient else ingredient["id"],  # type: ignore[typeddict-item]
        name=ingredient["ingredientNotation"],
        description=f"{cookidoo_quantity_from_json(ingredient['quantity'])} {ingredient['unitNotation']}"
        if "unitNotation" in ingredient
        and ingredient["unitNotation"]
        and "quantity" in ingredient
        and ingredient["quantity"]
        else cookidoo_quantity_from_json(ingredient["quantity"])
        if "quantity" in ingredient and ingredient["quantity"]
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
        if "unitNotation" in item
        and item["unitNotation"]
        and "quantity" in item
        and item["quantity"]
        else str(cookidoo_quantity_from_json(item["quantity"]))
        if "quantity" in item and item["quantity"]
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
    localization: CookidooLocalizationConfig | None = None,
) -> CookidooCalendarDay:
    """Convert a calendar day received from the API to a cookidoo item."""

    def _to_day_recipe(recipe: CalenderDayRecipeJSON) -> CookidooCalendarDayRecipe:
        assets = recipe["assets"]
        thumbnail, image = None, None
        descriptive_assets = [assets["images"]] if assets and assets["images"] else None
        if descriptive_assets is not None:
            thumbnail, image = _extract_images_from_descriptive_assets(
                descriptive_assets
            )

        url = _construct_recipe_url(localization, recipe["id"])

        return CookidooCalendarDayRecipe(
            id=recipe["id"],
            name=recipe["title"],
            total_time=recipe["totalTime"],
            thumbnail=thumbnail,
            image=image,
            url=url,
        )

    regular_recipes = [_to_day_recipe(recipe) for recipe in calendar_day["recipes"]]
    custom_recipes = [
        _to_day_recipe(recipe) for recipe in calendar_day.get("customerRecipes", [])
    ]

    return CookidooCalendarDay(
        id=calendar_day["id"],
        title=calendar_day["title"],
        recipes=[*regular_recipes, *custom_recipes],
        customer_recipe_ids=list(calendar_day.get("customerRecipeIds", [])),
    )


def cookidoo_create_custom_recipe_to_json(
    recipe: CookidooCreateCustomRecipe,
) -> CreateCustomRecipeRequestJSON:
    """Convert a create custom recipe input to a JSON payload for the API.

    The Cookidoo API creates a blank recipe with just a name.
    The recipe details are then set via a separate PATCH call.
    """
    return {"recipeName": recipe.name}


def cookidoo_edit_custom_recipe_to_json(
    recipe: CookidooEditCustomRecipe,
    existing: CookidooCustomRecipe,
) -> EditCustomRecipeRequestJSON:
    """Convert an edit custom recipe input to a JSON payload for the API.

    Merges the edit fields with the existing recipe, keeping existing values
    for any fields not specified in the edit.
    """
    name = recipe.name if recipe.name is not None else existing.name
    ingredients = (
        recipe.ingredients if recipe.ingredients is not None else existing.ingredients
    )
    instructions = (
        recipe.instructions
        if recipe.instructions is not None
        else existing.instructions
    )
    serving_size = (
        recipe.serving_size
        if recipe.serving_size is not None
        else existing.serving_size
    )
    total_time = (
        recipe.total_time if recipe.total_time is not None else existing.total_time
    )
    active_time = (
        recipe.active_time if recipe.active_time is not None else existing.active_time
    )
    tools = recipe.tools if recipe.tools is not None else existing.tools
    unit_text = recipe.unit_text or "portion"

    cook_time = max(0, total_time - active_time)

    return {
        "name": name,
        "image": recipe.image,
        "isImageOwnedByUser": recipe.image is not None,
        "tools": tools,
        "yield": {"value": serving_size, "unitText": unit_text},
        "prepTime": active_time,
        "cookTime": cook_time,
        "totalTime": total_time,
        "ingredients": [{"type": "INGREDIENT", "text": ing} for ing in ingredients],
        "instructions": [{"type": "STEP", "text": step} for step in instructions],
        "hints": None,
        "workStatus": "PRIVATE",
        "recipeMetadata": {"requiresAnnotationsCheck": False},
    }


def cookidoo_create_custom_recipe_edit_to_json(
    recipe: CookidooCreateCustomRecipe,
) -> EditCustomRecipeRequestJSON:
    """Convert a create custom recipe input to an edit JSON payload.

    Used after creating a blank recipe to set its full details via PATCH.
    """
    cook_time = max(0, recipe.total_time - recipe.active_time)

    # Convert instructions - handle both strings and CookidooInstruction objects
    instructions = []
    for step in recipe.instructions:
        if isinstance(step, CookidooInstruction):
            # Build settings text for presets (duplicated format)
            settings_parts = []
            if step.settings:
                if step.settings.time is not None:
                    if step.settings.time < 60:
                        settings_parts.append(f"{step.settings.time} sec")
                        time_str = str(step.settings.time)
                    else:
                        mins = step.settings.time // 60
                        settings_parts.append(f"{mins} min")
                        time_str = str(mins)
                else:
                    time_str = ""
                if step.settings.temperature is not None:
                    settings_parts.append(str(step.settings.temperature))
                if step.settings.speed is not None:
                    settings_parts.append(f"speed {step.settings.speed}")
            
            if settings_parts:
                settings_text = "/".join(settings_parts)
                # Simple format - show settings once
                # Example: "Chop. 5 sec/speed 5"
                text = f"{step.text}. {settings_text}"
            else:
                text = step.text
            
            step_dict: dict = {"type": "STEP", "text": text}
            instructions.append(step_dict)
        else:
            instructions.append({"type": "STEP", "text": step})

    return {
        "name": recipe.name,
        "image": recipe.image,
        "isImageOwnedByUser": recipe.image is not None,
        "tools": recipe.tools,
        "yield": {"value": recipe.serving_size, "unitText": recipe.unit_text},
        "prepTime": recipe.active_time,
        "cookTime": cook_time,
        "totalTime": recipe.total_time,
        "ingredients": [
            {"type": "INGREDIENT", "text": ing} for ing in recipe.ingredients
        ],
        "instructions": instructions,
        "hints": None,
        "workStatus": "PRIVATE",
        "recipeMetadata": {"requiresAnnotationsCheck": False},
    }


def cookidoo_custom_recipes_from_json(
    data: CustomRecipesResponseJSON,
    localization: CookidooLocalizationConfig | None = None,
) -> list[CookidooCustomRecipe]:
    """Convert a custom recipes list response from the API to a list of custom recipes."""
    return [
        cookidoo_custom_recipe_from_json(item, localization) for item in data["items"]
    ]


async def __get_localization_options(
    country: str | None = None,
    language: str | None = None,
) -> list[CookidooLocalizationConfig]:
    async with aiofiles.open(localization_file_path, encoding="utf-8") as file:
        options_ = cast(list[dict[str, str]], json.loads(await file.read()))
        options = (CookidooLocalizationConfig(**x) for x in options_)
        filtered_options = filter(
            lambda option: (
                (not country or option.country_code == country)
                and (not language or option.language == language)
            ),
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
