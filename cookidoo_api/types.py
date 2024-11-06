"""Cookidoo API types."""

from typing import TypedDict


class CookidooLocalizationConfig(TypedDict):
    """A localization config class."""

    country_code: str
    language: str
    url: str


class CookidooConfig(TypedDict):
    """Cookidoo config type.

    Attributes
    ----------
    localization
        The localization for the api including country, language and url
    email
        The email to login
    password
        The password to login

    """

    localization: CookidooLocalizationConfig
    email: str
    password: str


class CookidooAuthResponse(TypedDict):
    """An auth response class."""

    username: str
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


class CookidooUserInfo(TypedDict):
    """A user info class."""

    username: str
    description: str | None
    picture: str | None


class CookidooSubscription(TypedDict):
    """A subscription class."""

    active: bool
    expires: str
    startDate: str
    status: str
    subscriptionLevel: str
    subscriptionSource: str
    type: str
    extendedType: str


class CookidooItem(TypedDict):
    """Cookidoo item type.

    Attributes
    ----------
    id
        The id of the item
    name
        The label of the item
    description
        The description of the item, including the quantity or other helpful information
    isOwned
        Whether the items is checked or not

    """

    id: str
    name: str
    description: str | None
    isOwned: bool


class CookidooRecipe(TypedDict):
    """Cookidoo recipe type.

    Attributes
    ----------
    id
        The id of the recipe
    name
        The label of the recipe
    ingredients
        The ingredients of the recipe

    """

    id: str
    name: str
    ingredients: list[CookidooItem]


class IngredientQuantityJSON(TypedDict):
    """The json for an ingredient quantity in the API."""

    value: int | float


class IngredientJSON(TypedDict):
    """The json for an ingredient in the API."""

    id: str
    ingredientNotation: str
    isOwned: bool
    quantity: IngredientQuantityJSON | None
    unitNotation: str | None


class RecipeJSON(TypedDict):
    """The json for a recipe in the API."""

    id: str
    title: str
    recipeIngredientGroups: list[IngredientJSON]
