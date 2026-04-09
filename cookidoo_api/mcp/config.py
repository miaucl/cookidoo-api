"""Configuration helpers for the Cookidoo MCP server."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import os
from typing import Self

from cookidoo_api.helpers import get_localization_options
from cookidoo_api.types import CookidooLocalizationConfig

COOKIDOO_EMAIL_ENV = "COOKIDOO_EMAIL"
COOKIDOO_PASSWORD_ENV = "COOKIDOO_PASSWORD"
COOKIDOO_COUNTRY_CODE_ENV = "COOKIDOO_COUNTRY_CODE"
COOKIDOO_LANGUAGE_ENV = "COOKIDOO_LANGUAGE"

LEGACY_EMAIL_ENV = "EMAIL"
LEGACY_PASSWORD_ENV = "PASSWORD"


class CookidooMCPConfigError(ValueError):
    """Raised when the MCP server configuration is invalid."""


@dataclass(frozen=True)
class CookidooMCPConfig:
    """Configuration for the local Cookidoo MCP server."""

    email: str | None = None
    password: str | None = None
    country_code: str | None = None
    language: str | None = None

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> Self:
        """Load configuration from the current process environment."""
        source = os.environ if environ is None else environ
        return cls(
            email=_first_non_blank(source, COOKIDOO_EMAIL_ENV, LEGACY_EMAIL_ENV),
            password=_first_non_blank(
                source, COOKIDOO_PASSWORD_ENV, LEGACY_PASSWORD_ENV
            ),
            country_code=_first_non_blank(source, COOKIDOO_COUNTRY_CODE_ENV),
            language=_first_non_blank(source, COOKIDOO_LANGUAGE_ENV),
        )

    def require_credentials(self) -> tuple[str, str]:
        """Return configured credentials or raise a helpful error."""
        email = self.email
        password = self.password
        missing: list[str] = []
        if not email:
            missing.append(COOKIDOO_EMAIL_ENV)
        if not password:
            missing.append(COOKIDOO_PASSWORD_ENV)

        if missing:
            joined = ", ".join(missing)
            raise CookidooMCPConfigError(
                "Missing Cookidoo credentials. "
                f"Set {joined} (or the legacy EMAIL/PASSWORD names) before calling authenticated tools."
            )

        assert email is not None
        assert password is not None
        return email, password

    async def resolve_localization(self) -> CookidooLocalizationConfig:
        """Resolve the configured localization or fall back to the library default."""
        if self.country_code is None and self.language is None:
            return CookidooLocalizationConfig()

        matches = await get_localization_options(
            country=self.country_code,
            language=self.language,
        )

        if not matches:
            raise CookidooMCPConfigError(
                "No Cookidoo localization matched the configured "
                f"{_describe_filters(self.country_code, self.language)}. "
                "Use cookidoo_list_localizations to find a valid country/language pair."
            )

        if len(matches) > 1:
            raise CookidooMCPConfigError(
                "The configured localization "
                f"{_describe_filters(self.country_code, self.language)} matched {len(matches)} options. "
                f"Set both {COOKIDOO_COUNTRY_CODE_ENV} and {COOKIDOO_LANGUAGE_ENV} to a unique pair, "
                "or omit both to use the default localization."
            )

        return matches[0]


def _first_non_blank(source: Mapping[str, str], *names: str) -> str | None:
    """Return the first configured non-empty environment value."""
    for name in names:
        value = source.get(name)
        if value is not None and value.strip():
            return value.strip()
    return None


def _describe_filters(country_code: str | None, language: str | None) -> str:
    """Return a human-readable description of configured localization filters."""
    filters: list[str] = []
    if country_code is not None:
        filters.append(f"{COOKIDOO_COUNTRY_CODE_ENV}={country_code!r}")
    if language is not None:
        filters.append(f"{COOKIDOO_LANGUAGE_ENV}={language!r}")
    return ", ".join(filters)
