"""Cookidoo API package."""

__version__ = "0.7.0"

from .const import DEFAULT_COOKIDOO_CONFIG
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
    CookidooConfig,
    CookidooIngredientItem,
    CookidooItem,
    CookidooLocalizationConfig,
    CookidooRecipe,
    CookidooRecipeDetails,
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
    "CookidooRecipe",
    "CookidooRecipeDetails",
    "CookidooException",
    "CookidooConfigException",
    "CookidooAuthException",
    "CookidooParseException",
    "CookidooRequestException",
    "CookidooResponseException",
    "CookidooUnavailableException",
    "DEFAULT_COOKIDOO_CONFIG",
]
