"""Smoke test for cookidoo-api."""

from datetime import datetime

import pytest

from cookidoo_api.cookidoo import Cookidoo
from cookidoo_api.types import (
    CookidooAdditionalItem,
    CookidooCreateCustomRecipe,
    CookidooIngredientAnnotation,
    CookidooIngredientItem,
    CookidooInstruction,
    CookidooStepSettings,
    CookidooTTSAnnotation,
    CookidooUpdateCustomRecipe,
    ThermomixMachineType,
    ThermomixSpeed,
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

    async def test_cookidoo_search_recipes(self, cookidoo: Cookidoo) -> None:
        """Test cookidoo search recipes."""
        result = await cookidoo.search_recipes("Brötchen")
        assert hasattr(result, "recipes") and hasattr(result, "total")
        assert isinstance(result.recipes, list)
        assert isinstance(result.total, int)
        assert result.total >= len(result.recipes)
        if result.recipes:
            recipe = result.recipes[0]
            assert hasattr(recipe, "id") and hasattr(recipe, "name")

    async def test_cookidoo_list_custom_recipes(self, cookidoo: Cookidoo) -> None:
        """Test cookidoo list custom recipes."""
        recipes = await cookidoo.list_custom_recipes()

        assert isinstance(recipes, list)
        for recipe in recipes:
            assert recipe.id
            assert recipe.name

    async def test_cookidoo_create_custom_recipe(self, cookidoo: Cookidoo) -> None:
        """Test cookidoo create custom recipe from scratch, get and remove."""
        created = await cookidoo.create_custom_recipe(
            CookidooCreateCustomRecipe(
                name="Smoke test recipe",
                ingredients=["100g flour", "1 egg"],
                instructions=["Mix ingredients", "Bake 20 min"],
                serving_size=2,
                active_time=300,
                total_time=1200,
            )
        )
        try:
            assert created.id
            assert created.name == "Smoke test recipe"
            assert created.serving_size == 2
            assert created.ingredients == ["100g flour", "1 egg"]
            fetched = await cookidoo.get_custom_recipe(created.id)
            assert fetched.id == created.id
            assert fetched.name == "Smoke test recipe"
            edited = await cookidoo.update_custom_recipe(
                created.id,
                CookidooUpdateCustomRecipe(name="Edited smoke test recipe"),
            )
            assert edited.id == created.id
            assert edited.name == "Edited smoke test recipe"
            listed = await cookidoo.list_custom_recipes()
            assert any(recipe.id == created.id for recipe in listed)
        finally:
            await cookidoo.remove_custom_recipe(created.id)

    async def test_cookidoo_create_custom_recipe_with_annotations(
        self, cookidoo: Cookidoo
    ) -> None:
        """Test create/update with structured steps, annotations, and machine tools."""
        created = await cookidoo.create_custom_recipe(
            CookidooCreateCustomRecipe(
                name="Smoke annotated recipe",
                ingredients=["100g flour", "1 egg"],
                instructions=[
                    CookidooInstruction(
                        "Add 100g flour",
                        annotations=[
                            CookidooIngredientAnnotation("100g flour", "100g flour")
                        ],
                    ),
                    CookidooInstruction(
                        "Mix 1 min/speed 4",
                        settings=CookidooStepSettings(
                            time=60,
                            speed=ThermomixSpeed.SPEED_4,
                        ),
                        annotations=[
                            CookidooTTSAnnotation(
                                "1 min/speed 4",
                                time=60,
                                speed=ThermomixSpeed.SPEED_4,
                            )
                        ],
                    ),
                    "Serve warm",
                ],
                serving_size=2,
                active_time=180,
                total_time=600,
                tools=[ThermomixMachineType.TM6, ThermomixMachineType.TM7],
                hints=["Smoke test hint"],
            )
        )
        try:
            assert created.id
            assert created.name == "Smoke annotated recipe"
            assert set(created.tools) >= {"TM6", "TM7"}
            assert len(created.instructions) == 3
            assert created.hints == ["Smoke test hint"]

            updated = await cookidoo.update_custom_recipe(
                created.id,
                CookidooUpdateCustomRecipe(
                    name="Edited annotated smoke recipe",
                    serving_size=4,
                    instructions=[
                        CookidooInstruction(
                            "Mix 2 min/speed 5",
                            settings=CookidooStepSettings(
                                time=120,
                                speed=ThermomixSpeed.SPEED_5,
                            ),
                            annotations=[
                                CookidooTTSAnnotation(
                                    "2 min/speed 5",
                                    time=120,
                                    speed=ThermomixSpeed.SPEED_5,
                                )
                            ],
                        )
                    ],
                    hints=["Updated smoke hint"],
                ),
            )
            assert updated.id == created.id
            assert updated.name == "Edited annotated smoke recipe"
            assert updated.serving_size == 4
            assert len(updated.instructions) == 1
            assert updated.hints == ["Updated smoke hint"]

            fetched = await cookidoo.get_custom_recipe(created.id)
            assert fetched.name == "Edited annotated smoke recipe"
            assert fetched.serving_size == 4
            assert fetched.hints == ["Updated smoke hint"]
        finally:
            await cookidoo.remove_custom_recipe(created.id)

    async def test_cookidoo_add_custom_recipe_from(self, cookidoo: Cookidoo) -> None:
        """Test cookidoo create a custom recipe by copying an existing recipe."""
        search = await cookidoo.search_recipes("Brötchen", page_size=1)
        assert search.recipes, "Expected at least one searchable recipe to copy"
        source_recipe_id = search.recipes[0].id

        created = await cookidoo.add_custom_recipe_from(source_recipe_id, 4)
        try:
            assert created.id
            assert created.serving_size == 4
            assert created.name

            fetched = await cookidoo.get_custom_recipe(created.id)
            assert fetched.id == created.id
            assert fetched.name == created.name

            listed = await cookidoo.list_custom_recipes()
            assert any(recipe.id == created.id for recipe in listed)
        finally:
            await cookidoo.remove_custom_recipe(created.id)

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
