"""Smoke test for cookidoo-api."""

from cookidoo_api.cookidoo import Cookidoo


class TestMethods:
    """Test methods."""

    async def test_cookidoo_clear_shopping_list(self, cookidoo: Cookidoo) -> None:
        """Test cookidoo clear shopping_ ist before testing of all methods."""
        await cookidoo.clear_shopping_list()

    async def test_cookidoo_get_user_info(self, cookidoo: Cookidoo) -> None:
        """Test cookidoo get user info."""
        user_info = await cookidoo.get_user_info()
        assert "API" in user_info["username"]

    async def test_cookidoo_get_active_subscription(self, cookidoo: Cookidoo) -> None:
        """Test cookidoo get active subscription."""
        sub = await cookidoo.get_active_subscription()
        assert sub is None  # Test account uses the free plan

    async def test_cookidoo_recipe_details(self, cookidoo: Cookidoo) -> None:
        """Test cookidoo recipe details."""
        recipe_details = await cookidoo.get_recipe_details("r59322")
        assert isinstance(recipe_details, object)
        assert recipe_details["id"] == "r59322"
        assert recipe_details["name"] == "Vollwert-Brötchen/Baguettes"

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
            added_ingredient["name"] for added_ingredient in added_ingredients
        )
        edited_ingredients = await cookidoo.edit_ingredient_items_ownership(
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
        assert isinstance(edited_ingredients, list)
        assert len(edited_ingredients) == 1
        assert edited_ingredients[0]["is_owned"]

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
            added_ingredient["name"] for added_ingredient in added_additional_items
        )
        assert "Fisch" in (
            added_ingredient["name"] for added_ingredient in added_additional_items
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
        assert isinstance(edited_additional_items, list)
        assert len(edited_additional_items) == 1
        assert edited_additional_items[0]["is_owned"]

        edited_additional_items = await cookidoo.edit_additional_items(
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
        assert isinstance(edited_additional_items, list)
        assert len(edited_additional_items) == 1
        assert edited_additional_items[0]["name"] == "Vogel"

        additional_items = await cookidoo.get_additional_items()
        assert isinstance(additional_items, list)
        assert len(additional_items) == 2

        await cookidoo.remove_additional_items(
            [
                added_additional_item["id"]
                for added_additional_item in added_additional_items
            ]
        )

        additional_items = await cookidoo.get_additional_items()
        assert isinstance(additional_items, list)
        assert len(additional_items) == 0
