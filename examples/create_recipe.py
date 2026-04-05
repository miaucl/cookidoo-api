"""Example: Create a recipe and add it to a collection."""

import asyncio

import aiohttp

from cookidoo_api import Cookidoo, CookidooConfig, CookidooLocalizationConfig
from cookidoo_api.types import CookidooCreateCustomRecipe

# Your Cookidoo credentials
EMAIL = "your@email.com"
PASSWORD = "yourpassword"

# Collection to add recipe to (find yours with get_custom_collections())
COLLECTION_ID = "your-collection-id"


async def main():
    """Create a recipe and add it to a collection."""

    # Setup config
    cfg = CookidooConfig(
        email=EMAIL,
        password=PASSWORD,
        localization=CookidooLocalizationConfig(
            country_code="ch",
            language="de-CH",
            url="https://cookidoo.ch/foundation/de-CH",
        ),
    )

    async with aiohttp.ClientSession() as session:
        api = Cookidoo(session, cfg)
        await api.login()
        print("Logged in")

        # Create a custom recipe
        recipe = CookidooCreateCustomRecipe(
            name="Chicken with Egg Noodles (Thermomix)",
            serving_size=6,
            total_time=95 * 60,  # 95 minutes total
            active_time=30 * 60,  # 30 minutes active prep
            unit_text="portion",  # IMPORTANT: Must be exactly "portion"
            tools=["TM7", "TM6"],  # Works with both TM7 and TM6 models
            ingredients=[
                "1 whole chicken (~1.5 kg), cut into 10 pieces",
                "500 g egg noodles",
                "1 onion",
                "2 cloves garlic",
                "2-3 sprigs oregano",
                "2-3 sprigs thyme",
                "4-6 tbsp olive oil",
                "6 allspice berries",
                "1 cinnamon stick",
                "1 chicken bouillon cube",
                "1/2 tbsp granulated sugar",
                "1 tbsp tomato paste",
                "100 g white wine",
                "1 litre boiling water",
                "500 g crushed tomatoes",
                "salt and pepper to taste",
                "crumbled feta cheese (for serving)",
                "finely chopped parsley (for serving)",
            ],
            instructions=[
                "Chop onion and garlic: Place in the bowl. 5 sec / Speed 5. Scrape down the sides.",
                "Saute aromatics: Add 2-3 tbsp olive oil, oregano, thyme. 3 min / Varoma / Speed 1.",
                "Saute chicken: Remove the aromatics. Brown the chicken pieces in a pan with a little olive oil, 2-3 min per side. Place in the bowl with salt, pepper, allspice, cinnamon. 5 min / Varoma / Reverse / Speed 0.5.",
                "Sauce and simmer: Add sugar, tomato paste, wine, 400 g water, crushed tomatoes, chicken bouillon cube. 35 min / 100C / Reverse / Speed 0.5.",
                "Preheat oven to 200C fan. In a 30x40 cm baking tray, combine egg noodles + 600 g water + chicken with sauce. Mix well.",
                "Bake at 200C for 20-25 minutes until the liquid is absorbed and the noodles are golden.",
                "Serving: Top with crumbled feta cheese and finely chopped parsley. Enjoy!",
            ],
        )

        result = await api.create_custom_recipe(recipe)
        print(f"Recipe created: {result.id}")
        print(f"   Name: {result.name}")
        print(f"   Ingredients: {len(result.ingredients)}")
        print(f"   Instructions: {len(result.instructions)}")

        # Add to collection
        await api.add_recipes_to_custom_collection(COLLECTION_ID, [result.id])
        print("Added to collection")

        print("\nDone!")
        print(f"   URL: https://cookidoo.ch/created-recipes/de-CH/{result.id}")


if __name__ == "__main__":
    asyncio.run(main())
