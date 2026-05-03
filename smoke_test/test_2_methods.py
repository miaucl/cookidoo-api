"""Smoke test for cookidoo-api."""

from datetime import datetime, timedelta

import pytest

from cookidoo_api.cookidoo import Cookidoo
from cookidoo_api.types import (
    CookidooAdditionalItem,
    CookidooCreateCustomRecipe,
    CookidooEditCustomRecipe,
    CookidooIngredientItem,
    CookidooInstruction,
    CookidooStepSettings,
)


class TestMethods:
    """Test methods."""

    async def test_cookidoo_clear_shopping_list(self, cookidoo: Cookidoo) -> None:
        """Test cookidoo clear shopping_ ist before testing of all methods."""
        await cookidoo.clear_shopping_list()

    async def test_cookidoo_get_user_info(self, cookidoo: Cookidoo) -> None:
        """Test cookidoo get user info."""
        user_info = await cookidoo.get_user_info()
        assert "API" in user_info.username

    async def test_cookidoo_get_active_subscription(self, cookidoo: Cookidoo) -> None:
        """Test cookidoo get active subscription."""
        sub = await cookidoo.get_active_subscription()
        if sub is not None:  # Test account uses the free plan or a trial
            assert sub.status == "ACTIVE"
            assert sub.type == "TRIAL"
        else:
            assert sub is None

    @pytest.mark.parametrize(
        (
            "recipe_id",
            "name",
        ),
        [
            ("r59322", "Vollwert-Brötchen/Baguettes"),
            ("r628448", "Salmorejo de sandía con cubo de Rubik"),
        ],
    )
    async def test_cookidoo_recipe_details(
        self, cookidoo: Cookidoo, recipe_id: str, name: str
    ) -> None:
        """Test cookidoo recipe details."""
        recipe_details = await cookidoo.get_recipe_details(recipe_id)
        assert isinstance(recipe_details, object)
        assert recipe_details.id == recipe_id
        assert recipe_details.name == name

    async def test_cookidoo_shopping_list_recipe_and_ingredients(
        self, cookidoo: Cookidoo
    ) -> None:
        """Test cookidoo shopping list recipe and ingredients."""
        added_ingredients = await cookidoo.add_ingredient_items_for_recipes(
            ["r59322", "r907016"]
        )
        assert isinstance(added_ingredients, list)
        assert len(added_ingredients) == 14
        assert "Zucker" in (
            added_ingredient.name for added_ingredient in added_ingredients
        )
        edited_ingredients = await cookidoo.edit_ingredient_items_ownership(
            [
                CookidooIngredientItem(
                    **{**ingredient.__dict__, "is_owned": not ingredient.is_owned},
                )
                for ingredient in filter(
                    lambda ingredient: ingredient.name == "Hefe",
                    added_ingredients,
                )
            ]
        )
        assert isinstance(edited_ingredients, list)
        assert len(edited_ingredients) == 1
        assert edited_ingredients[0].is_owned

        ingredients = await cookidoo.get_ingredient_items()
        assert isinstance(ingredients, list)
        assert len(ingredients) == 14

        recipes = await cookidoo.get_shopping_list_recipes()
        assert isinstance(recipes, list)
        assert len(recipes) == 2

        await cookidoo.remove_ingredient_items_for_recipes(["r59322", "r907016"])
        ingredients_empty = await cookidoo.get_ingredient_items()
        assert isinstance(ingredients_empty, list)
        assert len(ingredients_empty) == 0

    async def test_cookidoo_additional_items(self, cookidoo: Cookidoo) -> None:
        """Test cookidoo additional items."""
        added_additional_items = await cookidoo.add_additional_items(
            ["Fleisch", "Fisch"]
        )
        assert isinstance(added_additional_items, list)
        assert len(added_additional_items) == 2
        assert "Fleisch" in (
            added_ingredient.name for added_ingredient in added_additional_items
        )
        assert "Fisch" in (
            added_ingredient.name for added_ingredient in added_additional_items
        )

        edited_additional_items = await cookidoo.edit_additional_items_ownership(
            [
                CookidooAdditionalItem(
                    **{
                        **additional_item.__dict__,
                        "is_owned": not additional_item.is_owned,
                    },
                )
                for additional_item in filter(
                    lambda additional_item: additional_item.name == "Fisch",
                    added_additional_items,
                )
            ]
        )
        assert isinstance(edited_additional_items, list)
        assert len(edited_additional_items) == 1
        assert edited_additional_items[0].is_owned

        edited_additional_items = await cookidoo.edit_additional_items(
            [
                CookidooAdditionalItem(
                    **{
                        **additional_item.__dict__,
                        "name": "Vogel",
                    },
                )
                for additional_item in filter(
                    lambda additional_item: additional_item.name == "Fisch",
                    edited_additional_items,
                )
            ]
        )
        assert isinstance(edited_additional_items, list)
        assert len(edited_additional_items) == 1
        assert edited_additional_items[0].name == "Vogel"

        additional_items = await cookidoo.get_additional_items()
        assert isinstance(additional_items, list)
        assert len(additional_items) == 2

        await cookidoo.remove_additional_items(
            [
                added_additional_item.id
                for added_additional_item in added_additional_items
            ]
        )

        additional_items = await cookidoo.get_additional_items()
        assert isinstance(additional_items, list)
        assert len(additional_items) == 0

    async def test_cookidoo_managed_collections(self, cookidoo: Cookidoo) -> None:
        """Test cookidoo managed collections."""
        added_managed_collection = await cookidoo.add_managed_collection("col500401")
        assert added_managed_collection.id == "col500401"

        managed_collections = await cookidoo.get_managed_collections()
        assert isinstance(managed_collections, list)
        assert len(managed_collections) == 1

        count_collections, count_pages = await cookidoo.count_managed_collections()
        assert count_collections == 1
        assert count_pages == 1

        await cookidoo.remove_managed_collection("col500401")

        managed_collections = await cookidoo.get_managed_collections()
        assert isinstance(managed_collections, list)
        assert len(managed_collections) == 0

    async def test_cookidoo_custom_collections(self, cookidoo: Cookidoo) -> None:
        """Test cookidoo custom collections."""
        added_custom_collection = await cookidoo.add_custom_collection(
            "TEST_COLLECTION"
        )
        assert added_custom_collection.name == "TEST_COLLECTION"

        custom_collections = await cookidoo.get_custom_collections()
        assert isinstance(custom_collections, list)
        assert len(custom_collections) == 1

        count_collections, count_pages = await cookidoo.count_custom_collections()
        assert count_collections == 1
        assert count_pages == 1

        custom_collection_with_recipe = await cookidoo.add_recipes_to_custom_collection(
            added_custom_collection.id, ["r907015"]
        )
        assert custom_collection_with_recipe.chapters[0].recipes[0].id == "r907015"
        custom_collection_without_recipe = (
            await cookidoo.remove_recipe_from_custom_collection(
                added_custom_collection.id, "r907015"
            )
        )
        assert len(custom_collection_without_recipe.chapters[0].recipes) == 0

        await cookidoo.remove_custom_collection(added_custom_collection.id)

        custom_collections = await cookidoo.get_custom_collections()
        assert isinstance(custom_collections, list)
        assert len(custom_collections) == 0

    async def test_cookidoo_calendar(self, cookidoo: Cookidoo) -> None:
        """Test cookidoo calendar."""
        added_day_recipes = await cookidoo.add_recipes_to_calendar(
            datetime.now().date(), ["r907015", "r59322"]
        )
        assert len(added_day_recipes.recipes) == 2
        assert [recipe.id for recipe in added_day_recipes.recipes] == [
            "r907015",
            "r59322",
        ]

        day_recipes = await cookidoo.get_recipes_in_calendar_week(datetime.now().date())
        assert isinstance(day_recipes, list)
        assert len(day_recipes) == 1
        assert [recipe.id for recipe in day_recipes[0].recipes] == [
            "r907015",
            "r59322",
        ]

        await cookidoo.remove_recipe_from_calendar(datetime.now().date(), "r907015")
        await cookidoo.remove_recipe_from_calendar(datetime.now().date(), "r59322")

        day_recipes = await cookidoo.get_recipes_in_calendar_week(datetime.now().date())
        assert isinstance(day_recipes, list)
        assert len(day_recipes) == 0

    async def test_cookidoo_create_custom_recipe_with_structured_steps(
        self, cookidoo: Cookidoo
    ) -> None:
        """Test creating a custom recipe with structured step settings."""
        recipe = CookidooCreateCustomRecipe(
            name=f"Structured Test Recipe {datetime.now().isoformat()}",
            serving_size=4,
            total_time=3600,
            active_time=1800,
            unit_text="portion",
            tools=["TM6"],
            ingredients=[
                "500g chicken breast",
                "200g vegetables",
                "100ml olive oil",
            ],
            instructions=[
                CookidooInstruction(
                    text="Chop vegetables finely",
                    settings=CookidooStepSettings(time=10, speed=5),
                ),
                CookidooInstruction(
                    text="Saut\u00e9 chicken",
                    settings=CookidooStepSettings(time=600, temperature=100, speed=1),
                ),
                CookidooInstruction(
                    text="Final cook with Varoma",
                    settings=CookidooStepSettings(
                        time=1200, temperature="Varoma", speed=0.5
                    ),
                ),
            ],
        )

        result = await cookidoo.create_custom_recipe(recipe)
        assert result.id is not None
        assert result.name == recipe.name
        assert result.serving_size == 4

        # Cleanup
        await cookidoo.remove_custom_recipe(result.id)

    async def test_cookidoo_create_and_edit_custom_recipe(
        self, cookidoo: Cookidoo
    ) -> None:
        """Test full custom recipe creation and editing workflow."""
        # Create initial recipe
        recipe = CookidooCreateCustomRecipe(
            name=f"Edit Test {datetime.now().isoformat()}",
            serving_size=2,
            total_time=1800,
            active_time=600,
            unit_text="portion",
            tools=["TM6"],
            ingredients=["100g flour", "2 eggs"],
            instructions=["Mix ingredients", "Bake at 180\u00b0C"],
        )

        created = await cookidoo.create_custom_recipe(recipe)
        assert created.id is not None

        # Edit the recipe
        updates = CookidooEditCustomRecipe(
            name=f"Updated {created.name}",
            serving_size=4,
            ingredients=["200g flour", "4 eggs", "100g sugar"],
            instructions=["Mix all ingredients", "Bake at 200\u00b0C for 30 min"],
        )

        edited = await cookidoo.edit_custom_recipe(created.id, updates)
        assert edited.name == updates.name
        assert edited.serving_size == 4

        # Cleanup
        await cookidoo.remove_custom_recipe(created.id)

    async def test_cookidoo_list_and_manage_custom_recipes(
        self, cookidoo: Cookidoo
    ) -> None:
        """Test listing and managing custom recipes."""
        # Get initial count
        initial_recipes = await cookidoo.get_custom_recipes()
        initial_count = len(initial_recipes)

        # Create a test recipe
        recipe = CookidooCreateCustomRecipe(
            name=f"List Test {datetime.now().isoformat()}",
            serving_size=2,
            total_time=900,
            active_time=300,
            unit_text="portion",
            tools=["TM6"],
            ingredients=["Ingredient 1", "Ingredient 2"],
            instructions=["Step 1", "Step 2"],
        )

        created = await cookidoo.create_custom_recipe(recipe)

        # Verify it appears in list
        updated_recipes = await cookidoo.get_custom_recipes()
        assert len(updated_recipes) == initial_count + 1
        assert any(r.id == created.id for r in updated_recipes)

        # Cleanup
        await cookidoo.remove_custom_recipe(created.id)

        # Verify removal
        final_recipes = await cookidoo.get_custom_recipes()
        assert len(final_recipes) == initial_count

    async def test_cookidoo_calendar_multiple_days(self, cookidoo: Cookidoo) -> None:
        """Test adding recipes to multiple calendar days."""
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)

        # Add recipes to different days
        await cookidoo.add_recipes_to_calendar(today, ["r59322"])
        await cookidoo.add_recipes_to_calendar(tomorrow, ["r907015"])

        # Verify both appear in week view
        week_recipes = await cookidoo.get_recipes_in_calendar_week(today)
        day_ids = [d.id for d in week_recipes]
        assert today.isoformat() in day_ids
        assert tomorrow.isoformat() in day_ids

        # Cleanup
        await cookidoo.remove_recipe_from_calendar(today, "r59322")
        await cookidoo.remove_recipe_from_calendar(tomorrow, "r907015")

    async def test_cookidoo_invalid_recipe_id(self, cookidoo: Cookidoo) -> None:
        """Test handling of invalid recipe IDs."""
        with pytest.raises(Exception):
            await cookidoo.get_recipe_details("invalid-id-12345")
