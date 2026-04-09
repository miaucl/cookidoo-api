"""Tool registration and handlers for the Cookidoo MCP server."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from datetime import date

from fastmcp import FastMCP
from fastmcp.tools import ToolResult

from cookidoo_api.cookidoo import Cookidoo
from cookidoo_api.helpers import get_localization_options
from cookidoo_api.types import (
    CookidooCollection,
    CookidooSearchFilters,
    CookidooSearchSort,
)

from .errors import to_tool_error
from .serialization import make_tool_result
from .session import CookidooSessionManager

LOCAL_READONLY_ANNOTATIONS = {
    "readOnlyHint": True,
    "idempotentHint": True,
    "openWorldHint": False,
}

API_READONLY_ANNOTATIONS = {
    "readOnlyHint": True,
    "idempotentHint": True,
    "openWorldHint": True,
}

API_MUTATION_ANNOTATIONS = {
    "openWorldHint": True,
}

API_DESTRUCTIVE_ANNOTATIONS = {
    "openWorldHint": True,
    "destructiveHint": True,
}


def register_tools(mcp: FastMCP, session_manager: CookidooSessionManager) -> None:
    """Register the Cookidoo MCP tool set."""

    @mcp.tool(annotations=LOCAL_READONLY_ANNOTATIONS)
    async def cookidoo_list_localizations(
        country_code: str | None = None,
        language: str | None = None,
    ) -> ToolResult:
        """List valid Cookidoo localizations filtered by optional country code and language. Use this before configuring authenticated tools."""
        return await _run_tool(
            handle_list_localizations(
                country_code=country_code,
                language=language,
            )
        )

    @mcp.tool(annotations=API_READONLY_ANNOTATIONS)
    async def cookidoo_get_account_summary() -> ToolResult:
        """Fetch the authenticated Cookidoo profile and active subscription. Use cookidoo_list_localizations first if localization is misconfigured."""
        return await _run_tool(handle_get_account_summary(session_manager))

    @mcp.tool(annotations=API_READONLY_ANNOTATIONS)
    async def cookidoo_get_recipe_details(recipe_id: str) -> ToolResult:
        """Fetch detailed Cookidoo recipe metadata by recipe ID. Use this when you already know the recipe ID."""
        return await _run_tool(
            handle_get_recipe_details(
                session_manager=session_manager,
                recipe_id=recipe_id,
            )
        )

    @mcp.tool(annotations=API_READONLY_ANNOTATIONS)
    async def cookidoo_search_recipes(
        query: str = "",
        page: int = 0,
        page_size: int = 20,
        sort: str | None = None,
        category: str | None = None,
        difficulty: str | None = None,
        max_total_time_minutes: int | None = None,
        max_prep_time_minutes: int | None = None,
        tm_version: str | None = None,
        accessories: list[str] | None = None,
        portions: int | None = None,
        min_rating: int | None = None,
    ) -> ToolResult:
        """Search Cookidoo recipes by keyword with optional filters. Use this to discover recipes before adding them to shopping lists, collections, or calendars. Sort options: relevance, newest, name_asc, rating, total_time, prep_time. Categories use IDs like VrkNavCategory-RPF-003. Difficulty: easy, medium, advanced. TM versions: TM7, TM6, TM5, TM31."""
        return await _run_tool(
            handle_search_recipes(
                session_manager=session_manager,
                query=query,
                page=page,
                page_size=page_size,
                sort=sort,
                category=category,
                difficulty=difficulty,
                max_total_time_minutes=max_total_time_minutes,
                max_prep_time_minutes=max_prep_time_minutes,
                tm_version=tm_version,
                accessories=accessories,
                portions=portions,
                min_rating=min_rating,
            )
        )

    @mcp.tool(annotations=API_READONLY_ANNOTATIONS)
    async def cookidoo_get_shopping_list() -> ToolResult:
        """Return the current shopping list snapshot including recipe entries, ingredient items, and additional items. Use mutation tools to change it."""
        return await _run_tool(handle_get_shopping_list(session_manager))

    @mcp.tool(annotations=API_READONLY_ANNOTATIONS)
    async def cookidoo_list_custom_collections() -> ToolResult:
        """List all custom Cookidoo collections across pages. Does not include managed collections."""
        return await _run_tool(handle_list_custom_collections(session_manager))

    @mcp.tool(annotations=API_READONLY_ANNOTATIONS)
    async def cookidoo_get_calendar_week(day: date) -> ToolResult:
        """Fetch the Cookidoo calendar week containing the provided date."""
        return await _run_tool(
            handle_get_calendar_week(
                session_manager=session_manager,
                day=day,
            )
        )

    @mcp.tool(annotations=API_MUTATION_ANNOTATIONS)
    async def cookidoo_add_recipe_ingredients_to_shopping_list(
        recipe_ids: list[str],
    ) -> ToolResult:
        """Add ingredient items for one or more recipe IDs to the shopping list. Use cookidoo_get_shopping_list to inspect the updated state."""
        return await _run_tool(
            handle_add_recipe_ingredients_to_shopping_list(
                session_manager=session_manager,
                recipe_ids=recipe_ids,
            )
        )

    @mcp.tool(annotations=API_DESTRUCTIVE_ANNOTATIONS)
    async def cookidoo_remove_recipe_ingredients_from_shopping_list(
        recipe_ids: list[str],
    ) -> ToolResult:
        """Remove shopping-list ingredient items for one or more recipe IDs. Use cookidoo_clear_shopping_list to remove everything instead."""
        return await _run_tool(
            handle_remove_recipe_ingredients_from_shopping_list(
                session_manager=session_manager,
                recipe_ids=recipe_ids,
            )
        )

    @mcp.tool(annotations=API_DESTRUCTIVE_ANNOTATIONS)
    async def cookidoo_clear_shopping_list() -> ToolResult:
        """Clear the entire shopping list. This removes current shopping-list entries rather than just one recipe."""
        return await _run_tool(handle_clear_shopping_list(session_manager))

    @mcp.tool(annotations=API_MUTATION_ANNOTATIONS)
    async def cookidoo_create_custom_collection(name: str) -> ToolResult:
        """Create a new custom Cookidoo collection. Use cookidoo_list_custom_collections to inspect existing collections."""
        return await _run_tool(
            handle_create_custom_collection(
                session_manager=session_manager,
                name=name,
            )
        )

    @mcp.tool(annotations=API_MUTATION_ANNOTATIONS)
    async def cookidoo_add_recipes_to_custom_collection(
        custom_collection_id: str,
        recipe_ids: list[str],
    ) -> ToolResult:
        """Add recipe IDs to an existing custom Cookidoo collection. Use cookidoo_create_custom_collection if you need a new collection first."""
        return await _run_tool(
            handle_add_recipes_to_custom_collection(
                session_manager=session_manager,
                custom_collection_id=custom_collection_id,
                recipe_ids=recipe_ids,
            )
        )

    @mcp.tool(annotations=API_DESTRUCTIVE_ANNOTATIONS)
    async def cookidoo_remove_recipe_from_custom_collection(
        custom_collection_id: str,
        recipe_id: str,
    ) -> ToolResult:
        """Remove a recipe ID from a custom Cookidoo collection. Use cookidoo_list_custom_collections to find valid collection IDs."""
        return await _run_tool(
            handle_remove_recipe_from_custom_collection(
                session_manager=session_manager,
                custom_collection_id=custom_collection_id,
                recipe_id=recipe_id,
            )
        )

    @mcp.tool(annotations=API_MUTATION_ANNOTATIONS)
    async def cookidoo_add_recipes_to_calendar(
        day: date,
        recipe_ids: list[str],
    ) -> ToolResult:
        """Schedule one or more recipe IDs on a calendar date. Use cookidoo_get_calendar_week to inspect the surrounding week."""
        return await _run_tool(
            handle_add_recipes_to_calendar(
                session_manager=session_manager,
                day=day,
                recipe_ids=recipe_ids,
            )
        )

    @mcp.tool(annotations=API_DESTRUCTIVE_ANNOTATIONS)
    async def cookidoo_remove_recipe_from_calendar(
        day: date,
        recipe_id: str,
    ) -> ToolResult:
        """Remove a recipe ID from a calendar date. Use cookidoo_add_recipes_to_calendar to schedule recipes instead."""
        return await _run_tool(
            handle_remove_recipe_from_calendar(
                session_manager=session_manager,
                day=day,
                recipe_id=recipe_id,
            )
        )


async def handle_list_localizations(
    country_code: str | None = None,
    language: str | None = None,
) -> ToolResult:
    """Return matching localization options."""
    localizations = await get_localization_options(
        country=country_code,
        language=language,
    )
    return make_tool_result(
        summary=(
            f"Found {len(localizations)} Cookidoo localization option(s) "
            "matching the requested filters."
        ),
        payload={
            "country_code": country_code,
            "language": language,
            "count": len(localizations),
            "localizations": localizations,
        },
    )


async def handle_get_account_summary(
    session_manager: CookidooSessionManager,
) -> ToolResult:
    """Return the authenticated account summary."""
    client = await session_manager.get_client()
    user_info, subscription = await asyncio.gather(
        client.get_user_info(),
        client.get_active_subscription(),
    )
    return make_tool_result(
        summary=f"Loaded Cookidoo account summary for {user_info.username}.",
        payload={
            "user_info": user_info,
            "subscription": subscription,
        },
    )


async def handle_get_recipe_details(
    session_manager: CookidooSessionManager,
    recipe_id: str,
) -> ToolResult:
    """Return detailed recipe metadata."""
    client = await session_manager.get_client()
    recipe = await client.get_recipe_details(recipe_id)
    return make_tool_result(
        summary=f"Loaded Cookidoo recipe details for {recipe.name} ({recipe.id}).",
        payload={"recipe": recipe},
    )


async def handle_search_recipes(
    session_manager: CookidooSessionManager,
    query: str,
    page: int,
    page_size: int,
    sort: str | None,
    category: str | None,
    difficulty: str | None,
    max_total_time_minutes: int | None,
    max_prep_time_minutes: int | None,
    tm_version: str | None,
    accessories: list[str] | None,
    portions: int | None,
    min_rating: int | None,
) -> ToolResult:
    """Search for recipes via Algolia."""
    client = await session_manager.get_client()

    search_sort = CookidooSearchSort(sort) if sort else CookidooSearchSort.RELEVANCE

    filters = CookidooSearchFilters(
        category=category,
        difficulty=difficulty,
        max_total_time=max_total_time_minutes * 60 if max_total_time_minutes else None,
        max_prep_time=max_prep_time_minutes * 60 if max_prep_time_minutes else None,
        tm_version=tm_version,
        accessories=accessories,
        portions=portions,
        min_rating=min_rating,
    )

    result = await client.search_recipes(
        query=query,
        page=page,
        page_size=page_size,
        sort=search_sort,
        filters=filters,
    )

    return make_tool_result(
        summary=(
            f"Found {result.total_hits} recipe(s) matching '{query}'. "
            f"Showing page {result.page + 1}/{result.total_pages} "
            f"({len(result.hits)} hit(s))."
        ),
        payload={
            "query": query,
            "total_hits": result.total_hits,
            "page": result.page,
            "total_pages": result.total_pages,
            "hits": result.hits,
        },
    )


async def handle_get_shopping_list(
    session_manager: CookidooSessionManager,
) -> ToolResult:
    """Return shopping-list data from the Cookidoo account."""
    client = await session_manager.get_client()
    recipes, ingredient_items, additional_items = await asyncio.gather(
        client.get_shopping_list_recipes(),
        client.get_ingredient_items(),
        client.get_additional_items(),
    )
    return make_tool_result(
        summary=(
            "Loaded the Cookidoo shopping list with "
            f"{len(recipes)} recipe entry/entries, "
            f"{len(ingredient_items)} ingredient item(s), and "
            f"{len(additional_items)} additional item(s)."
        ),
        payload={
            "recipes": recipes,
            "ingredient_items": ingredient_items,
            "additional_items": additional_items,
        },
    )


async def handle_list_custom_collections(
    session_manager: CookidooSessionManager,
) -> ToolResult:
    """Return all custom collections across pages."""
    client = await session_manager.get_client()
    collections = await _get_all_custom_collections(client)
    return make_tool_result(
        summary=f"Loaded {len(collections)} custom Cookidoo collection(s).",
        payload={
            "count": len(collections),
            "collections": collections,
        },
    )


async def handle_get_calendar_week(
    session_manager: CookidooSessionManager,
    day: date,
) -> ToolResult:
    """Return the calendar week around the provided date."""
    client = await session_manager.get_client()
    calendar_days = await client.get_recipes_in_calendar_week(day)
    return make_tool_result(
        summary=(
            f"Loaded {len(calendar_days)} calendar day entry/entries for the week containing {day.isoformat()}."
        ),
        payload={
            "day": day,
            "calendar_days": calendar_days,
        },
    )


async def handle_add_recipe_ingredients_to_shopping_list(
    session_manager: CookidooSessionManager,
    recipe_ids: list[str],
) -> ToolResult:
    """Add recipe ingredients to the shopping list."""
    client = await session_manager.get_client()
    ingredient_items = await client.add_ingredient_items_for_recipes(recipe_ids)
    return make_tool_result(
        summary=(
            f"Added ingredient items for {len(recipe_ids)} recipe(s) to the shopping list."
        ),
        payload={
            "recipe_ids": recipe_ids,
            "ingredient_items": ingredient_items,
        },
    )


async def handle_remove_recipe_ingredients_from_shopping_list(
    session_manager: CookidooSessionManager,
    recipe_ids: list[str],
) -> ToolResult:
    """Remove recipe ingredients from the shopping list."""
    client = await session_manager.get_client()
    await client.remove_ingredient_items_for_recipes(recipe_ids)
    return make_tool_result(
        summary=(
            f"Removed shopping-list ingredient items for {len(recipe_ids)} recipe(s)."
        ),
        payload={
            "recipe_ids": recipe_ids,
            "removed": True,
        },
    )


async def handle_clear_shopping_list(
    session_manager: CookidooSessionManager,
) -> ToolResult:
    """Clear the shopping list."""
    client = await session_manager.get_client()
    await client.clear_shopping_list()
    return make_tool_result(
        summary="Cleared the Cookidoo shopping list.",
        payload={"cleared": True},
    )


async def handle_create_custom_collection(
    session_manager: CookidooSessionManager,
    name: str,
) -> ToolResult:
    """Create a custom collection."""
    client = await session_manager.get_client()
    collection = await client.add_custom_collection(name)
    return make_tool_result(
        summary=f"Created custom collection {collection.name} ({collection.id}).",
        payload={"collection": collection},
    )


async def handle_add_recipes_to_custom_collection(
    session_manager: CookidooSessionManager,
    custom_collection_id: str,
    recipe_ids: list[str],
) -> ToolResult:
    """Add recipes to a custom collection."""
    client = await session_manager.get_client()
    collection = await client.add_recipes_to_custom_collection(
        custom_collection_id,
        recipe_ids,
    )
    return make_tool_result(
        summary=(
            f"Added {len(recipe_ids)} recipe(s) to custom collection {collection.name} ({collection.id})."
        ),
        payload={
            "collection": collection,
            "recipe_ids": recipe_ids,
        },
    )


async def handle_remove_recipe_from_custom_collection(
    session_manager: CookidooSessionManager,
    custom_collection_id: str,
    recipe_id: str,
) -> ToolResult:
    """Remove a recipe from a custom collection."""
    client = await session_manager.get_client()
    collection = await client.remove_recipe_from_custom_collection(
        custom_collection_id,
        recipe_id,
    )
    return make_tool_result(
        summary=(
            f"Removed recipe {recipe_id} from custom collection {collection.name} ({collection.id})."
        ),
        payload={
            "collection": collection,
            "recipe_id": recipe_id,
        },
    )


async def handle_add_recipes_to_calendar(
    session_manager: CookidooSessionManager,
    day: date,
    recipe_ids: list[str],
) -> ToolResult:
    """Add recipes to a calendar day."""
    client = await session_manager.get_client()
    calendar_day = await client.add_recipes_to_calendar(day, recipe_ids)
    return make_tool_result(
        summary=f"Scheduled {len(recipe_ids)} recipe(s) on {day.isoformat()}.",
        payload={
            "day": day,
            "recipe_ids": recipe_ids,
            "calendar_day": calendar_day,
        },
    )


async def handle_remove_recipe_from_calendar(
    session_manager: CookidooSessionManager,
    day: date,
    recipe_id: str,
) -> ToolResult:
    """Remove a recipe from a calendar day."""
    client = await session_manager.get_client()
    calendar_day = await client.remove_recipe_from_calendar(day, recipe_id)
    return make_tool_result(
        summary=f"Removed recipe {recipe_id} from {day.isoformat()}.",
        payload={
            "day": day,
            "recipe_id": recipe_id,
            "calendar_day": calendar_day,
        },
    )


async def _run_tool(operation: Awaitable[ToolResult]) -> ToolResult:
    """Execute a tool handler and convert known failures into ToolError."""
    try:
        return await operation
    except Exception as error:
        raise to_tool_error(error) from error


async def _get_all_custom_collections(client: Cookidoo) -> list[CookidooCollection]:
    """Load all custom collections across pages."""
    total_collections, total_pages = await client.count_custom_collections()
    if total_pages == 0 or total_collections == 0:
        return []

    collections: list[CookidooCollection] = []
    for page in range(total_pages):
        collections.extend(await client.get_custom_collections(page=page))
    return collections
