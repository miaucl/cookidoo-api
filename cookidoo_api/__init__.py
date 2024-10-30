"""Cookidoo API package."""

__version__ = "0.3.0"

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
from .types import (
    CookidooAuthResponse,
    CookidooConfig,
    CookidooItem,
    CookidooItemStateType,
)

__all__ = [
    "Cookidoo",
    "CookidooItemStateType",
    "CookidooConfig",
    "CookidooAuthResponse",
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
