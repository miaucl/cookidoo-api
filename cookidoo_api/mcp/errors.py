"""Error translation for the Cookidoo MCP server."""

from __future__ import annotations

from fastmcp.exceptions import ToolError

from cookidoo_api.exceptions import (
    CookidooAuthException,
    CookidooConfigException,
    CookidooParseException,
    CookidooRequestException,
)

from .config import CookidooMCPConfigError


def to_tool_error(error: Exception) -> ToolError:
    """Map known Cookidoo exceptions to recoverable MCP tool errors."""
    if isinstance(error, ToolError):
        return error

    if isinstance(error, CookidooMCPConfigError):
        return ToolError(str(error))

    if isinstance(error, CookidooConfigException):
        return ToolError(
            f"{error} Verify your MCP environment configuration and retry."
        )

    if isinstance(error, CookidooAuthException):
        return ToolError(
            f"{error} Verify your Cookidoo credentials and localization, then retry."
        )

    if isinstance(error, CookidooRequestException):
        return ToolError(f"{error} The Cookidoo service may be unavailable. Retry later.")

    if isinstance(error, CookidooParseException):
        return ToolError(
            f"{error} The unofficial Cookidoo response format may have changed."
        )

    return ToolError("Unexpected Cookidoo MCP error. Please retry.")
