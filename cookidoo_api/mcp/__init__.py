"""Cookidoo MCP server support."""

from .config import (
    COOKIDOO_COUNTRY_CODE_ENV,
    COOKIDOO_EMAIL_ENV,
    COOKIDOO_LANGUAGE_ENV,
    COOKIDOO_PASSWORD_ENV,
    CookidooMCPConfig,
    CookidooMCPConfigError,
)
from .server import create_server, run

__all__ = [
    "COOKIDOO_COUNTRY_CODE_ENV",
    "COOKIDOO_EMAIL_ENV",
    "COOKIDOO_LANGUAGE_ENV",
    "COOKIDOO_PASSWORD_ENV",
    "CookidooMCPConfig",
    "CookidooMCPConfigError",
    "create_server",
    "run",
]
