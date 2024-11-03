"""Cookidoo API exceptions."""


class CookidooException(Exception):
    """General exception occurred."""


class CookidooConfigException(CookidooException):
    """When the config is invalid."""


class CookidooAuthException(CookidooException):
    """When an authentication error is encountered."""


class CookidooParseException(CookidooException):
    """When data could not be parsed."""


class CookidooRequestException(CookidooException):
    """When a request returns an error."""


class CookidooResponseException(CookidooException):
    """When a response could not be parsed."""


class CookidooUnavailableException(CookidooException):
    """When the network or server is not available."""
