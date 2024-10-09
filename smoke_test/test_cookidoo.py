"""Smoke test for cookidoo-api."""

from dotenv import load_dotenv

from cookidoo_api.cookidoo import Cookidoo
from smoke_test.conftest import (
    TEST_ADDITIONAL_ITEM_CREATE,
    TEST_ADDITIONAL_ITEM_LABEL,
    TEST_ITEM_DESCRIPTION,
    TEST_ITEM_LABEL,
    TEST_ITEMS_COUNT,
    TEST_RECIPE,
    save_cookies,
)

load_dotenv()


class TestLoginAndValidation:
    """Test login and validation."""

    async def test_cookidoo_login(self, cookidoo: Cookidoo) -> None:
        """Test cookidoo validation of the token or login otherwise."""
        await cookidoo.login()
        save_cookies(cookidoo.cookies)

    async def test_cookidoo_clear_items(self, cookidoo: Cookidoo) -> None:
        """Test cookidoo clear items before testing of all jobs."""
        await cookidoo.clear_items()
        save_cookies(cookidoo.cookies)

    async def test_cookidoo_items(self, cookidoo: Cookidoo) -> None:
        """Test cookidoo items."""
        assert (
            len(await cookidoo.get_items(pending=True, checked=True)) == 0
        ), "Check if not items present"
        await cookidoo.add_items(TEST_RECIPE)
        assert (
            len(await cookidoo.get_items(pending=True, checked=True))
            == TEST_ITEMS_COUNT
        ), "Check if added items are there"
        assert (
            len(await cookidoo.get_items(pending=True)) == TEST_ITEMS_COUNT
        ), "Check if added items are in pending"
        assert (
            len(await cookidoo.get_items(checked=True)) == 0
        ), "Check if added items are not in checked"
        items = await cookidoo.get_items(pending=True)
        item_test = next(
            (item for item in items if item["label"] == TEST_ITEM_LABEL),
            None,
        )
        assert item_test, "Check if specific item is there"
        assert (
            item_test["description"] == TEST_ITEM_DESCRIPTION
        ), "Check if specific item has correct description"
        assert item_test["state"] == "pending", "Check if specific item is pending"
        item_test["state"] = "checked"
        await cookidoo.update_items([item_test])
        await cookidoo.update_items([item_test])  # Does nothing, just to check
        assert (
            len(await cookidoo.get_items(pending=True)) == TEST_ITEMS_COUNT - 1
        ), "Check if specific item has been removed from pending"
        assert (
            len(await cookidoo.get_items(checked=True)) == 1
        ), "Check if specific item has been added to checked"
        item_test["state"] = "pending"
        await cookidoo.update_items([item_test])
        assert (
            len(await cookidoo.get_items(pending=True)) == TEST_ITEMS_COUNT
        ), "Check if specific item has been removed from checked"
        assert (
            len(await cookidoo.get_items(checked=True)) == 0
        ), "Check if specific item has been added to pending"
        await cookidoo.remove_items(TEST_RECIPE)
        assert (
            len(await cookidoo.get_items(pending=True, checked=True)) == 0
        ), "Check if all items have been removed"

        save_cookies(cookidoo.cookies)

    async def test_cookidoo_additional_items(self, cookidoo: Cookidoo) -> None:
        """Test cookidoo additional items."""
        assert (
            len(await cookidoo.get_additional_items(pending=True, checked=True)) == 0
        ), "Check if not additional items present"
        await cookidoo.create_additional_items(TEST_ADDITIONAL_ITEM_CREATE)
        assert len(
            await cookidoo.get_additional_items(pending=True, checked=True)
        ) == len(
            TEST_ADDITIONAL_ITEM_CREATE
        ), "Check if added additional items are there"
        assert len(await cookidoo.get_additional_items(pending=True)) == len(
            TEST_ADDITIONAL_ITEM_CREATE
        ), "Check if added additional items are in pending"
        assert (
            len(await cookidoo.get_additional_items(checked=True)) == 0
        ), "Check if added additional items are not in checked"
        additional_items = await cookidoo.get_additional_items(pending=True)
        additional_item_test = next(
            (
                additional_item
                for additional_item in additional_items
                if additional_item["label"] == TEST_ADDITIONAL_ITEM_LABEL
            ),
            None,
        )
        assert additional_item_test, "Check if specific additional item is there"
        assert not additional_item_test[
            "description"
        ], "Check if specific additional item has no description"
        assert (
            additional_item_test["state"] == "pending"
        ), "Check if specific additional item is pending"
        additional_item_test["state"] = "checked"
        additional_item_test["label"] = "Toblerone"
        await cookidoo.update_additional_items([additional_item_test])
        await cookidoo.update_additional_items(
            [additional_item_test]
        )  # Does nothing, just to check
        assert (
            len(await cookidoo.get_additional_items(pending=True))
            == len(TEST_ADDITIONAL_ITEM_CREATE) - 1
        ), "Check if specific additional item has been removed from pending"
        assert (
            len(await cookidoo.get_additional_items(checked=True)) == 1
        ), "Check if specific additional item has been added to checked"
        additional_item_test["state"] = "pending"
        await cookidoo.update_additional_items([additional_item_test])
        assert len(await cookidoo.get_additional_items(pending=True)) == len(
            TEST_ADDITIONAL_ITEM_CREATE
        ), "Check if specific additional item has been removed from checked"
        assert (
            len(await cookidoo.get_additional_items(checked=True)) == 0
        ), "Check if specific additional item has been added to pending"
        await cookidoo.delete_additional_items([additional_item_test])
        assert (
            len(await cookidoo.get_additional_items(pending=True, checked=True))
            == len(TEST_ADDITIONAL_ITEM_CREATE) - 1
        ), "Check if specific additional item has been deleted"
        additional_items_to_delete = await cookidoo.get_additional_items(
            pending=True, checked=True
        )
        await cookidoo.delete_additional_items(
            [additional_item["id"] for additional_item in additional_items_to_delete]
        )
        assert (
            len(await cookidoo.get_additional_items(pending=True, checked=True)) == 0
        ), "Check if additional items have been deleted"

        save_cookies(cookidoo.cookies)
