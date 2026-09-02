"""Cookidoo API helpers."""

from collections.abc import Mapping, Sequence
import json
import logging
import os
from typing import cast
from urllib.parse import urlparse

import aiofiles
import isodate

from cookidoo_api.raw_types import (
    AdditionalItemJSON,
    CalendarDayJSON,
    CalenderDayRecipeJSON,
    CommunityProfileJSON,
    CustomCollectionJSON,
    CustomRecipeContentJSON,
    CustomRecipeJSON,
    CustomRecipeTextJSON,
    DescriptiveAssetJSON,
    IngredientJSON,
    ItemJSON,
    ManagedCollectionJSON,
    QuantityJSON,
    RecipeDetailsJSON,
    RecipeJSON,
    SubscriptionJSON,
)
from cookidoo_api.types import (
    CookidooAdditionalItem,
    CookidooCalendarDay,
    CookidooCalendarDayRecipe,
    CookidooCategory,
    CookidooChapter,
    CookidooChapterRecipe,
    CookidooCollection,
    CookidooCustomAnnotation,
    CookidooCustomRecipe,
    CookidooDevice,
    CookidooIngredient,
    CookidooIngredientAnnotation,
    CookidooIngredientItem,
    CookidooInstruction,
    CookidooLocalizationConfig,
    CookidooModeAnnotation,
    CookidooNutrition,
    CookidooNutritionGroup,
    CookidooRecipeCollection,
    CookidooRecipeNutrition,
    CookidooSearchRecipeHit,
    CookidooSearchResult,
    CookidooShoppingRecipe,
    CookidooShoppingRecipeDetails,
    CookidooStepSettings,
    CookidooSubscription,
    CookidooTemperatureSetting,
    CookidooTTSAnnotation,
    CookidooUserInfo,
    ThermomixMachineType,
)

_LOGGER = logging.getLogger(__name__)

localization_file_path = os.path.join(os.path.dirname(__file__), "localization.json")


def normalize_list_param(value: str | list[str] | None) -> str | None:
    """Normalize list/string params to comma-separated string."""
    if value is None:
        return None
    if isinstance(value, list):
        return ",".join([v for v in value if v])
    return value


def normalize_tmv_param(
    value: ThermomixMachineType | str | list[ThermomixMachineType | str] | None,
) -> str | None:
    """Normalize TMV param to comma-separated string."""
    if value is None:
        return None
    if isinstance(value, list):
        normalized: list[str] = []
        for item in value:
            normalized.append(
                item.value if isinstance(item, ThermomixMachineType) else str(item)
            )
        return ",".join([v for v in normalized if v])
    return value.value if isinstance(value, ThermomixMachineType) else value


def cookidoo_user_info_from_json(
    profile: CommunityProfileJSON,
) -> CookidooUserInfo:
    """Convert a community profile received from the API to a cookidoo user info."""
    user_info = profile["userInfo"]
    return CookidooUserInfo(
        id=profile["id"],
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


def cookidoo_device_from_json(model: str) -> CookidooDevice:
    """Convert a device machine type received from the API to a cookidoo device.

    The devices endpoint returns bare machine-type strings (e.g. ``"TM7"``).
    """
    return CookidooDevice(type=ThermomixMachineType(model))


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


def cookidoo_search_result_from_json(
    data: Mapping[str, object],
    localization: CookidooLocalizationConfig | None = None,
) -> CookidooSearchResult:
    """Convert a search result received from the API to a CookidooSearchResult.

    The API may return recipes in ``data`` (search endpoint) or ``recipes``;
    total is optional and defaults to the number of valid parsed hits.

    Parameters
    ----------
    data
        The raw JSON response from the search API.
    localization
        Optional localization config used to construct recipe URLs.

    Returns
    -------
    CookidooSearchResult
        The parsed search result with recipe hits and total count.

    """
    if "data" in data:
        raw_recipes = data["data"]
    elif "recipes" in data:
        raw_recipes = data["recipes"]
    else:
        raw_recipes = []
    recipes_data: list[object] = raw_recipes if isinstance(raw_recipes, list) else []
    total_raw = data.get("total")
    hits: list[CookidooSearchRecipeHit] = []
    for item in recipes_data:
        if not isinstance(item, dict):
            continue
        recipe_id_raw = item.get("id", "")
        name_raw = item.get("title") or item.get("name", "")
        recipe_id = recipe_id_raw if isinstance(recipe_id_raw, str) else ""
        name = name_raw if isinstance(name_raw, str) else ""
        thumbnail, image = None, None
        descriptive_assets = item.get("descriptiveAssets")
        if descriptive_assets and isinstance(descriptive_assets, list):
            thumbnail, image = _extract_images_from_descriptive_assets(
                descriptive_assets
            )
        url = _construct_recipe_url(localization, recipe_id)
        hits.append(
            CookidooSearchRecipeHit(
                id=recipe_id,
                name=name,
                thumbnail=thumbnail,
                image=image,
                url=url,
            )
        )
    total = total_raw if isinstance(total_raw, int) else len(hits)
    return CookidooSearchResult(recipes=hits, total=total)


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


def _duration_to_seconds(value: str | int | float | None) -> int:
    """Convert API duration variants to seconds."""
    if value is None:
        return 0
    if isinstance(value, int | float):
        return int(value)
    if not value:
        return 0
    duration = isodate.parse_duration(value).total_seconds()
    return int(duration) if isinstance(duration, float) else 0


def _extract_custom_recipe_ingredients(
    value: Sequence[str | CustomRecipeTextJSON] | None,
) -> list[str]:
    """Extract ingredient text from API string and object variants."""
    if value is None:
        return []
    return [
        text
        for item in value
        if isinstance(text := item.get("text") if isinstance(item, dict) else item, str)
    ]


def _parse_annotation_temperature(
    value: object,
) -> CookidooTemperatureSetting | None:
    """Parse an annotation temperature object."""
    if not isinstance(value, Mapping):
        return None
    temperature = value.get("value")
    if not isinstance(temperature, int | str):
        return None
    unit = value.get("unit")
    return CookidooTemperatureSetting(
        value=temperature,
        unit=unit if isinstance(unit, str) else None,
    )


def _parse_custom_recipe_annotation(
    value: object, instruction_text: str
) -> (
    CookidooIngredientAnnotation
    | CookidooTTSAnnotation
    | CookidooModeAnnotation
    | CookidooCustomAnnotation
    | None
):
    """Parse a typed annotation while preserving unknown annotation data."""
    if not isinstance(value, Mapping):
        return None
    annotation_type = value.get("type")
    data = value.get("data")
    position = value.get("position")
    if not isinstance(annotation_type, str) or not isinstance(data, Mapping):
        return None

    slot = ""
    if isinstance(position, Mapping):
        offset = position.get("offset")
        length = position.get("length")
        if isinstance(offset, int) and isinstance(length, int):
            slot = instruction_text[offset : offset + length]
    name_value = value.get("name")
    name = name_value if isinstance(name_value, str) else None
    annotation_data = dict(data)

    if annotation_type == "INGREDIENT":
        description = annotation_data.get("description")
        if isinstance(description, str):
            return CookidooIngredientAnnotation(slot, description, name)
    if annotation_type == "TTS":
        time = annotation_data.get("time")
        speed = annotation_data.get("speed")
        direction = annotation_data.get("direction")
        return CookidooTTSAnnotation(
            slot=slot,
            time=time if isinstance(time, int) else None,
            temperature=_parse_annotation_temperature(
                annotation_data.get("temperature")
            ),
            speed=speed if isinstance(speed, str) else None,
            direction=direction if isinstance(direction, str) else None,
            name=name,
        )
    if annotation_type == "MODE":
        mode = name or annotation_data.get("mode") or ""
        time = annotation_data.get("time")
        speed = annotation_data.get("speed")
        direction = annotation_data.get("direction")
        power = annotation_data.get("power")
        accessory = annotation_data.get("accessory")
        return CookidooModeAnnotation(
            slot=slot,
            mode=mode if isinstance(mode, str) else str(mode),
            time=time if isinstance(time, int) else None,
            temperature=_parse_annotation_temperature(
                annotation_data.get("temperature")
            ),
            speed=speed if isinstance(speed, str) else None,
            direction=direction if isinstance(direction, str) else None,
            power=power if isinstance(power, str) else None,
            accessory=accessory if isinstance(accessory, str) else None,
            name=name,
        )
    return CookidooCustomAnnotation(
        type=annotation_type,
        slot=slot,
        data=annotation_data,
        name=name,
    )


def _parse_custom_recipe_instructions(
    value: object,
) -> list[str | CookidooInstruction]:
    """Parse plain and structured instruction response variants."""
    if not isinstance(value, Sequence) or isinstance(value, str):
        return []
    result: list[str | CookidooInstruction] = []
    for item in value:
        if isinstance(item, str):
            result.append(item)
            continue
        if not isinstance(item, Mapping):
            continue
        text = item.get("text")
        if not isinstance(text, str):
            continue
        time = item.get("time")
        temperature = item.get("temperature")
        speed = item.get("speed")
        settings = None
        if any(field is not None for field in (time, temperature, speed)):
            settings = CookidooStepSettings(
                time=time if isinstance(time, int) else None,
                temperature=(
                    temperature if isinstance(temperature, int | str) else None
                ),
                speed=speed if isinstance(speed, int | float | str) else None,
            )
        raw_annotations = item.get("annotations", [])
        annotations = (
            [
                annotation
                for raw_annotation in raw_annotations
                if (annotation := _parse_custom_recipe_annotation(raw_annotation, text))
                is not None
            ]
            if isinstance(raw_annotations, list)
            else []
        )
        result.append(CookidooInstruction(text, settings, annotations))
    return result


def cookidoo_custom_recipe_from_json(
    recipe: CustomRecipeJSON,
    localization: CookidooLocalizationConfig | None = None,
) -> CookidooCustomRecipe:
    """Convert a custom recipe received from the API to a cookidoo custom recipe."""
    recipe_content: CustomRecipeContentJSON = recipe["recipeContent"]
    total_time = _duration_to_seconds(recipe_content.get("totalTime"))
    active_time = _duration_to_seconds(recipe_content.get("prepTime"))

    thumbnail: str | None = None
    image: str | None = None

    image = recipe_content.get("image", None)
    if image:
        thumbnail, image = _process_image_url(image)

    url = _construct_recipe_url(localization, recipe["recipeId"], "created-recipes")
    raw_recipe_yield = recipe_content.get("recipeYield") or recipe_content.get("yield")
    recipe_yield: Mapping[str, object] = (
        cast(Mapping[str, object], raw_recipe_yield)
        if isinstance(raw_recipe_yield, Mapping)
        else {}
    )
    serving_size = recipe_yield.get("value", 0)
    unit_text = recipe_yield.get("unitText", "portion")

    raw_hints = recipe_content.get("hints")
    if isinstance(raw_hints, str):
        hints = raw_hints.splitlines()
    elif isinstance(raw_hints, list):
        hints = [hint for hint in raw_hints if isinstance(hint, str)]
    else:
        hints = []

    raw_metadata = recipe_content.get("recipeMetadata")
    metadata: Mapping[str, object] = (
        cast(Mapping[str, object], raw_metadata)
        if isinstance(raw_metadata, Mapping)
        else {}
    )
    raw_work_status = recipe.get("workStatus", "PRIVATE")

    return CookidooCustomRecipe(
        id=recipe["recipeId"],
        name=recipe_content["name"],
        ingredients=_extract_custom_recipe_ingredients(
            recipe_content.get("recipeIngredient")
            or recipe_content.get("ingredients", [])
        ),
        instructions=_parse_custom_recipe_instructions(
            recipe_content.get("instructions")
            or recipe_content.get("recipeInstructions", [])
        ),
        serving_size=serving_size if isinstance(serving_size, int) else 0,
        total_time=total_time,
        active_time=active_time,
        tools=recipe_content.get("tool") or recipe_content.get("tools", []),
        thumbnail=thumbnail,
        image=image,
        url=url,
        hints=hints,
        unit_text=unit_text if isinstance(unit_text, str) else "portion",
        image_owned_by_user=bool(recipe_content.get("isImageOwnedByUser", False)),
        work_status=raw_work_status if isinstance(raw_work_status, str) else "PRIVATE",
        requires_annotations_check=bool(
            metadata.get("requiresAnnotationsCheck", False)
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
