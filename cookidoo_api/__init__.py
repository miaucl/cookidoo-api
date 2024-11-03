"""Cookidoo API package."""

__version__ = "0.4.0"

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
    CookidooAuthResponse,
    CookidooConfig,
    CookidooItem,
    CookidooItemStateType,
    CookidooLocalizationConfig,
    CookidooSubscription,
    CookidooUserInfo,
)

__all__ = [
    "Cookidoo",
    "get_country_options",
    "get_language_options",
    "get_localization_options",
    "CookidooItemStateType",
    "CookidooLocalizationConfig",
    "CookidooConfig",
    "CookidooAuthResponse",
    "CookidooUserInfo",
    "CookidooSubscription",
    "CookidooItem",
    "CookidooException",
    "CookidooConfigException",
    "CookidooAuthException",
    "CookidooParseException",
    "CookidooRequestException",
    "CookidooResponseException",
    "CookidooUnavailableException",
    "DEFAULT_COOKIDOO_CONFIG",
]
