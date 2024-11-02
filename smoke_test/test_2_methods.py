"""Smoke test for cookidoo-api."""

from cookidoo_api.cookidoo import Cookidoo


class TestMethods:
    """Test methods."""

    async def test_cookidoo_clear_shopping_list(self, cookidoo_auth: Cookidoo) -> None:
        """Test cookidoo clear shopping_ ist before testing of all methods."""
        await cookidoo_auth.clear_shopping_list()

    async def test_cookidoo_get_user_info(self, cookidoo_auth: Cookidoo) -> None:
        """Test cookidoo get user info."""
        user_info = await cookidoo_auth.get_user_info()
        assert "API" in user_info["username"]

    async def test_cookidoo_get_active_subscription(
        self, cookidoo_auth: Cookidoo
    ) -> None:
        """Test cookidoo get active subscription."""
        sub = await cookidoo_auth.get_active_subscription()
        assert sub is None  # Test account uses the free plan

    async def test_cookidoo_ingredients(self, cookidoo_auth: Cookidoo) -> None:
        """Test cookidoo ingredients."""
        added_ingredients = await cookidoo_auth.add_ingredients_for_recipes(
            ["r59322", "r907016"]
        )
        assert isinstance(added_ingredients, list)
        assert len(added_ingredients) == 14
        assert "Zucker" in (
            added_ingredient["name"] for added_ingredient in added_ingredients
        )
        edited_ingredients = await cookidoo_auth.edit_ingredients_ownership(
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
        assert isinstance(edited_ingredients, list)
        assert len(edited_ingredients) == 1
        assert edited_ingredients[0]["isOwned"]

        ingredients = await cookidoo_auth.get_ingredients()
        assert isinstance(ingredients, list)
        assert len(ingredients) == 14

        await cookidoo_auth.remove_ingredients_for_recipes(["r59322", "r907016"])
        ingredients_empty = await cookidoo_auth.get_ingredients()
        assert isinstance(ingredients_empty, list)
        assert len(ingredients_empty) == 0

    async def test_cookidoo_additional_items(self, cookidoo_auth: Cookidoo) -> None:
        """Test cookidoo additional items."""
        added_additional_items = await cookidoo_auth.add_additional_items(
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

        edited_additional_items = await cookidoo_auth.edit_additional_items_ownership(
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
        assert isinstance(edited_additional_items, list)
        assert len(edited_additional_items) == 1
        assert edited_additional_items[0]["isOwned"]

        edited_additional_items = await cookidoo_auth.edit_additional_items(
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

        additional_items = await cookidoo_auth.get_additional_items()
        assert isinstance(additional_items, list)
        assert len(additional_items) == 2

        await cookidoo_auth.remove_additional_items(
            [
                added_additional_item["id"]
                for added_additional_item in added_additional_items
            ]
        )

        additional_items = await cookidoo_auth.get_additional_items()
        assert isinstance(additional_items, list)
        assert len(additional_items) == 0
