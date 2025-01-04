#!/usr/bin/env python3
"""Example script for cookidoo-api."""

import asyncio
import logging
import os
import sys

import aiohttp
from dotenv import load_dotenv

from cookidoo_api import Cookidoo
from cookidoo_api.helpers import (
    get_country_options,
    get_language_options,
    get_localization_options,
)
from cookidoo_api.types import CookidooConfig

load_dotenv()

# Configure the root logger
logging.basicConfig(
    level=logging.DEBUG,  # Set the logging level (DEBUG, INFO, WARNING, etc.)
    format="%(asctime)s [%(levelname)8s] %(name)s:%(lineno)s %(message)s",  # Format of the log messages
    handlers=[  # Specify the handlers for the logger
        logging.StreamHandler(sys.stdout)  # Output to stdout
    ],
)


async def main():
    """Run main example function."""
    async with aiohttp.ClientSession() as session:
        # Show all country_codes, languages and some localizations
        _country_codes = await get_country_options()
        _languages = await get_language_options()
        _localizations_ch = await get_localization_options(country="ch")
        _localizations_en = await get_localization_options(language="en")

        # Create Cookidoo instance with email and password
        cookidoo = Cookidoo(
            session,
            cfg=CookidooConfig(
                email=os.environ["EMAIL"],
                password=os.environ["PASSWORD"],
                localization=(
                    await get_localization_options(country="ma", language="en")
                )[0],
            ),
        )
        # Login
        await cookidoo.login()
        await cookidoo.refresh_token()

        # Info
        await cookidoo.get_user_info()
        await cookidoo.get_active_subscription()

        # Custom collections
        added_custom_collection = await cookidoo.add_custom_collection(
            "TEST_COLLECTION"
        )
        _custom_collections = await cookidoo.get_custom_collections()
        await cookidoo.add_recipes_to_custom_collection(
            added_custom_collection.id, ["r907015"]
        )
        _custom_collections = await cookidoo.get_custom_collections()
        await cookidoo.remove_recipe_from_custom_collection(
            added_custom_collection.id, "r907015"
        )
        _custom_collections = await cookidoo.get_custom_collections()
        await cookidoo.remove_custom_collection(added_custom_collection.id)
        return

        # Managed collections
        _added_managed_collection = await cookidoo.add_managed_collection("col500401")
        _managed_collections = await cookidoo.get_managed_collections()
        await cookidoo.remove_managed_collection("col500401")

        # Recipe details
        _recipe_details = await cookidoo.get_recipe_details("r59322")

        # Shopping list
        await cookidoo.clear_shopping_list()

        # Ingredients
        added_ingredients = await cookidoo.add_ingredient_items_for_recipes(
            ["r59322", "r907016"]
        )
        _edited_ingredients = await cookidoo.edit_ingredient_items_ownership(
            [
                {
                    **ingredient,
                    "is_owned": not ingredient["is_owned"],
                }
                for ingredient in filter(
                    lambda ingredient: ingredient["name"] == "Hefe",
                    added_ingredients,
                )
            ]
        )
        _ingredients = await cookidoo.get_ingredient_items()
        _recipes = await cookidoo.get_shopping_list_recipes()
        await cookidoo.remove_ingredient_items_for_recipes(["r59322"])

        # Additional items
        added_additional_items = await cookidoo.add_additional_items(
            ["Fleisch", "Fisch"]
        )
        edited_additional_items = await cookidoo.edit_additional_items_ownership(
            [
                {
                    **additional_item,
                    "is_owned": not additional_item["is_owned"],
                }
                for additional_item in filter(
                    lambda additional_item: additional_item["name"] == "Fisch",
                    added_additional_items,
                )
            ]
        )
        await cookidoo.edit_additional_items(
            [
                {
                    **additional_item,
                    "name": "Vogel",
                }
                for additional_item in filter(
                    lambda additional_item: additional_item["name"] == "Fisch",
                    edited_additional_items,
                )
            ]
        )
        _additional_items = await cookidoo.get_additional_items()
        await cookidoo.remove_additional_items(
            [
                added_additional_item["id"]
                for added_additional_item in added_additional_items
            ]
        )


asyncio.run(main())
