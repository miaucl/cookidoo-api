"""Cookidoo API package."""

__version__ = "0.16.0"

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
    CookidooSearchRecipeHit,
    CookidooSearchResult,
    CookidooShoppingRecipe,
    CookidooShoppingRecipeDetails,
    CookidooSubscription,
    CookidooUserInfo,
    ThermomixMachineType,
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
    "CookidooSearchRecipeHit",
    "CookidooSearchResult",
    "CookidooIngredient",
    "CookidooCollection",
    "CookidooException",
    "CookidooConfigException",
    "CookidooAuthException",
    "CookidooParseException",
    "CookidooRequestException",
    "CookidooResponseException",
    "CookidooUnavailableException",
    "ThermomixMachineType",
]
