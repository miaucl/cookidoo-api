"""Cookidoo API package."""

__version__ = "0.13.0"

from .cookidoo import Cookidoo
from .exceptions import (
    CookidooAuthException,
    CookidooConfigException,
    CookidooException,
    CookidooParseException,
    CookidooRequestException,
    CookidooResponseException,
    CookidooUnavailableException,
)
from .helpers import get_country_options, get_language_options, get_localization_options
from .types import (
    CookidooAdditionalItem,
    CookidooAuthResponse,
    CookidooCategory,
    CookidooChapter,
    CookidooChapterRecipe,
    CookidooCollection,
    CookidooConfig,
    CookidooIngredient,
    CookidooIngredientItem,
    CookidooItem,
    CookidooLocalizationConfig,
    CookidooRecipeCollection,
    CookidooShoppingRecipe,
    CookidooShoppingRecipeDetails,
    CookidooSubscription,
    CookidooUserInfo,
)

__all__ = [
    "Cookidoo",
    "get_country_options",
    "get_language_options",
    "get_localization_options",
    "CookidooLocalizationConfig",
    "CookidooConfig",
    "CookidooAuthResponse",
    "CookidooUserInfo",
    "CookidooSubscription",
    "CookidooItem",
    "CookidooAdditionalItem",
    "CookidooIngredientItem",
    "CookidooShoppingRecipe",
    "CookidooShoppingRecipeDetails",
    "CookidooCategory",
    "CookidooChapter",
    "CookidooChapterRecipe",
    "CookidooRecipeCollection",
    "CookidooIngredient",
    "CookidooCollection",
    "CookidooException",
    "CookidooConfigException",
    "CookidooAuthException",
    "CookidooParseException",
    "CookidooRequestException",
    "CookidooResponseException",
    "CookidooUnavailableException",
]
