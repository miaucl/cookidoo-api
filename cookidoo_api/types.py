"""Cookidoo API types."""

from typing import Literal, TypedDict

CookidooItemStateType = Literal["pending", "checked"]
"""Cookidoo item state type"""


class CookidooConfig(TypedDict):
    """Cookidoo config type.

    Attributes
    ----------
    country
        The country code to use for the api
    language
        The language code to use for the api
    email
        The email to login
    password
        The password to login

    """

    country: str
    language: str
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
