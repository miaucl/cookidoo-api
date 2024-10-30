"""Cookidoo API helpers."""

from cookidoo_api.types import CookidooItem, IngredientJSON


def cookidoo_item_from_ingredient(
    ingredient: IngredientJSON,
) -> CookidooItem:
    """Convert an ingredient received from the API to a cookidoo item."""
    return CookidooItem(
        id=ingredient["id"],
        name=ingredient["ingredientNotation"],
        isOwned=ingredient["isOwned"],
        description=f"{ingredient['quantity']['value']} {ingredient['unitNotation']}"
        if ingredient["unitNotation"] and ingredient["quantity"]
        else str(ingredient["quantity"]["value"])
        if ingredient["quantity"]
        else "",
    )
