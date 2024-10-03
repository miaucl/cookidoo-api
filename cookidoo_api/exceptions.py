"""Cookidoo API exceptions."""


class CookidooException(Exception):
    """General exception occurred."""


class CookidooConfigException(CookidooException):
    """When the config is invalid."""


class CookidooAuthException(CookidooException):
    """When an authentication error is encountered."""


class CookidooAuthBotDetectionException(CookidooAuthException):
    """When an authentication error is encountered due to bot detection."""


class CookidooSelectorException(CookidooException):
    """When an expected selector has not been found."""


class CookidooActionException(CookidooException):
    """When an expected action could not be performed."""


class CookidooUnexpectedStateException(CookidooException):
    """When an unexpected state is present."""


class CookidooUnavailableException(CookidooException):
    """When the network or server is not available."""
