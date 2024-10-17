"""Cookidoo API package."""

__version__ = "0.1.1"

from .const import (
    DEFAULT_COOKIDOO_CONFIG,
    DEFAULT_NETWORK_TIMEOUT,
    DEFAULT_RETRIES,
    DEFAULT_TIMEOUT,
)
from .cookidoo import Cookidoo
from .exceptions import (
    CookidooActionException,
    CookidooAuthBotDetectionException,
    CookidooAuthException,
    CookidooConfigException,
    CookidooException,
    CookidooNavigationException,
    CookidooSelectorException,
    CookidooUnavailableException,
    CookidooUnexpectedStateException,
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
    "CookidooUnexpectedStateException",
    "CookidooNavigationException",
    "DEFAULT_COOKIDOO_CONFIG",
    "DEFAULT_RETRIES",
    "DEFAULT_NETWORK_TIMEOUT",
    "DEFAULT_TIMEOUT",
]
