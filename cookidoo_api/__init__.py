"""Cookidoo API package."""

__version__ = "0.1.0"

from .const import DEFAULT_COOKIDOO_CONFIG
from .cookidoo import Cookidoo
from .exceptions import (
    CookidooActionException,
    CookidooAuthBotDetectionException,
    CookidooAuthException,
    CookidooConfigException,
    CookidooException,
    CookidooSelectorException,
    CookidooUnavailableException,
)
from .types import (
    CookidooBrowserType,
    CookidooCaptchaRecoveryType,
    CookidooConfig,
    CookidooItem,
    CookidooItemStateType,
)

__all__ = [
    "Cookidoo",
    "CookidooBrowserType",
    "CookidooCaptchaRecoveryType",
    "CookidooItemStateType",
    "CookidooConfig",
    "CookidooItem",
    "CookidooException",
    "CookidooConfigException",
    "CookidooAuthException",
    "CookidooAuthBotDetectionException",
    "CookidooSelectorException",
    "CookidooActionException",
    "CookidooUnavailableException",
    "DEFAULT_COOKIDOO_CONFIG",
]
