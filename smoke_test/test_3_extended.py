"""Extended smoke tests for cookidoo-api.

These tests run against the live API to validate end-to-end functionality.
Run with: pytest smoke_test/test_3_extended.py -v
"""

from datetime import datetime, timedelta

import pytest

from cookidoo_api.cookidoo import Cookidoo
from cookidoo_api.types import (
    CookidooCreateCustomRecipe,
    CookidooEditCustomRecipe,
    CookidooInstruction,
    CookidooStepSettings,
)


class TestExtendedRecipeOperations:
    """Extended tests for custom recipe CRUD operations."""

    async def test_create_recipe_with_structured_steps(self, cookidoo: Cookidoo) -> None:
        """Test creating a recipe with structured step settings."""
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
                    text="Sauté chicken",
                    settings=CookidooStepSettings(
                        time=600, temperature=100, speed=1
                    ),
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

    async def test_create_and_edit_recipe(self, cookidoo: Cookidoo) -> None:
        """Test full recipe creation and editing workflow."""
        # Create initial recipe
        recipe = CookidooCreateCustomRecipe(
            name=f"Edit Test {datetime.now().isoformat()}",
            serving_size=2,
            total_time=1800,
            active_time=600,
            unit_text="portion",
            tools=["TM6"],
            ingredients=["100g flour", "2 eggs"],
            instructions=["Mix ingredients", "Bake at 180°C"],
        )

        created = await cookidoo.create_custom_recipe(recipe)
        assert created.id is not None

        # Edit the recipe
        updates = CookidooEditCustomRecipe(
            name=f"Updated {created.name}",
            serving_size=4,
            ingredients=["200g flour", "4 eggs", "100g sugar"],
            instructions=["Mix all ingredients", "Bake at 200°C for 30 min"],
        )

        edited = await cookidoo.edit_custom_recipe(created.id, updates)
        assert edited.name == updates.name
        assert edited.serving_size == 4

        # Cleanup
        await cookidoo.remove_custom_recipe(created.id)

    async def test_list_and_manage_custom_recipes(self, cookidoo: Cookidoo) -> None:
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


class TestExtendedCalendarOperations:
    """Extended tests for calendar functionality."""

    async def test_calendar_week_operations(self, cookidoo: Cookidoo) -> None:
        """Test calendar week retrieval and management."""
        today = datetime.now().date()
        
        # Get current week
        week_recipes = await cookidoo.get_recipes_in_calendar_week(today)
        initial_count = len(week_recipes)

        # Add recipe to today
        added = await cookidoo.add_recipes_to_calendar(today, ["r59322"])
        assert len(added.recipes) == 1
        assert added.recipes[0].id == "r59322"

        # Verify it appears in week view
        week_recipes = await cookidoo.get_recipes_in_calendar_week(today)
        today_entry = next((d for d in week_recipes if d.id == today.isoformat()), None)
        assert today_entry is not None
        assert any(r.id == "r59322" for r in today_entry.recipes)

        # Cleanup
        await cookidoo.remove_recipe_from_calendar(today, "r59322")

    async def test_calendar_multiple_days(self, cookidoo: Cookidoo) -> None:
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


class TestExtendedShoppingListOperations:
    """Extended tests for shopping list functionality."""

    async def test_shopping_list_full_workflow(self, cookidoo: Cookidoo) -> None:
        """Test complete shopping list workflow."""
        # Clear existing list
        await cookidoo.clear_shopping_list()
        
        ingredients = await cookidoo.get_ingredient_items()
        assert len(ingredients) == 0

        # Add recipes to shopping list
        await cookidoo.add_ingredient_items_for_recipes(["r59322"])
        
        ingredients = await cookidoo.get_ingredient_items()
        assert len(ingredients) > 0

        # Mark some as owned
        to_edit = [
            ingredient for ingredient in ingredients[:2]
        ]
        for ing in to_edit:
            ing.is_owned = True

        edited = await cookidoo.edit_ingredient_items_ownership(to_edit)
        assert all(e.is_owned for e in edited)

        # Clear and verify
        await cookidoo.clear_shopping_list()
        ingredients = await cookidoo.get_ingredient_items()
        assert len(ingredients) == 0

    async def test_additional_items_workflow(self, cookidoo: Cookidoo) -> None:
        """Test additional items (non-recipe) workflow."""
        # Clear existing
        await cookidoo.clear_shopping_list()

        # Add custom items
        added = await cookidoo.add_additional_items(["Milk", "Bread", "Eggs"])
        assert len(added) == 3

        # Get and verify
        items = await cookidoo.get_additional_items()
        assert len(items) == 3
        assert any(i.name == "Milk" for i in items)

        # Edit ownership
        to_edit = [items[0]]
        to_edit[0].is_owned = True
        edited = await cookidoo.edit_additional_items_ownership(to_edit)
        assert edited[0].is_owned

        # Edit name
        to_edit[0].name = "Organic Milk"
        renamed = await cookidoo.edit_additional_items(to_edit)
        assert renamed[0].name == "Organic Milk"

        # Remove all
        await cookidoo.remove_additional_items([i.id for i in items])
        remaining = await cookidoo.get_additional_items()
        assert len(remaining) == 0


class TestCollectionManagement:
    """Extended tests for collection management."""

    async def test_collection_full_lifecycle(self, cookidoo: Cookidoo) -> None:
        """Test complete collection lifecycle."""
        collection_name = f"Test Collection {datetime.now().isoformat()}"

        # Create collection
        collection = await cookidoo.add_custom_collection(collection_name)
        assert collection.name == collection_name

        # Add recipes
        with_recipes = await cookidoo.add_recipes_to_custom_collection(
            collection.id, ["r59322", "r907015"]
        )
        assert len(with_recipes.chapters[0].recipes) == 2

        # Remove one recipe
        with_one = await cookidoo.remove_recipe_from_custom_collection(
            collection.id, "r59322"
        )
        assert len(with_one.chapters[0].recipes) == 1

        # Remove collection
        await cookidoo.remove_custom_collection(collection.id)

        # Verify removal
        collections = await cookidoo.get_custom_collections()
        assert not any(c.id == collection.id for c in collections)

    async def test_managed_collections(self, cookidoo: Cookidoo) -> None:
        """Test managed collections (curated collections)."""
        # Add a managed collection
        added = await cookidoo.add_managed_collection("col500401")
        assert added.id == "col500401"

        # Get list
        collections = await cookidoo.get_managed_collections()
        assert any(c.id == "col500401" for c in collections)

        # Count
        count, pages = await cookidoo.count_managed_collections()
        assert count >= 1

        # Remove
        await cookidoo.remove_managed_collection("col500401")

        # Verify removal
        collections = await cookidoo.get_managed_collections()
        assert not any(c.id == "col500401" for c in collections)


class TestErrorHandling:
    """Tests for error handling in live API."""

    async def test_invalid_recipe_id(self, cookidoo: Cookidoo) -> None:
        """Test handling of invalid recipe IDs."""
        with pytest.raises(Exception):  # Should raise appropriate exception
            await cookidoo.get_recipe_details("invalid-id-12345")

    async def test_empty_collection_operations(self, cookidoo: Cookidoo) -> None:
        """Test operations on empty collections."""
        # Create empty collection
        collection = await cookidoo.add_custom_collection(
            f"Empty Test {datetime.now().isoformat()}"
        )

        # Get recipes (should be empty)
        recipes = await cookidoo.get_custom_collections()
        found = next((c for c in recipes if c.id == collection.id), None)
        assert found is not None
        assert len(found.chapters[0].recipes) == 0

        # Cleanup
        await cookidoo.remove_custom_collection(collection.id)

    async def test_calendar_edge_dates(self, cookidoo: Cookidoo) -> None:
        """Test calendar operations with edge dates."""
        # Far future date
        far_future = datetime(2030, 12, 31).date()
        
        # Try to add (API may accept or reject)
        try:
            result = await cookidoo.add_recipes_to_calendar(far_future, ["r59322"])
            # If accepted, cleanup
            await cookidoo.remove_recipe_from_calendar(far_future, "r59322")
        except Exception:
            # Expected behavior if API rejects far future dates
            pass
