#!/usr/bin/env python3
"""Example script for cookidoo-api."""

import asyncio
import logging
import os
import sys

import aiohttp
from dotenv import load_dotenv

from cookidoo_api import DEFAULT_COOKIDOO_CONFIG, Cookidoo
from cookidoo_api.helpers import (
    get_country_options,
    get_language_options,
    get_localization_options,
)

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
            {
                **DEFAULT_COOKIDOO_CONFIG,
                "email": os.environ["EMAIL"],
                "password": os.environ["PASSWORD"],
            },
        )
        # Login
        await cookidoo.login()
        await cookidoo.refresh_token()

        # Info
        await cookidoo.get_user_info()
        await cookidoo.get_active_subscription()

        # Shopping list
        await cookidoo.clear_shopping_list()

        # Ingredients
        added_ingredients = await cookidoo.add_ingredients_for_recipes(
            ["r59322", "r907016"]
        )
        _edited_ingredients = await cookidoo.edit_ingredients_ownership(
            [
                {
                    **ingredient,
                    "isOwned": not ingredient["isOwned"],
                }
                for ingredient in filter(
                    lambda ingredient: ingredient["name"] == "Hefe",
                    added_ingredients,
                )
            ]
        )
        _ingredients = await cookidoo.get_ingredients()
        _recipes = await cookidoo.get_shopping_list_recipes()
        await cookidoo.remove_ingredients_for_recipes(["r59322"])

        # Additional items
        added_additional_items = await cookidoo.add_additional_items(
            ["Fleisch", "Fisch"]
        )
        edited_additional_items = await cookidoo.edit_additional_items_ownership(
            [
                {
                    **additional_item,
                    "isOwned": not additional_item["isOwned"],
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
