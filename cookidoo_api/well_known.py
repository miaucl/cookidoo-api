"""Discovery of Cookidoo API endpoints via the ``.well-known/home`` HAL documents.

Cookidoo's backend exposes a `HAL <https://en.wikipedia.org/wiki/Hypertext_Application_Language>`_
``.well-known/home`` document per microservice (e.g. ``shopping``, ``planning``,
``organize``), listing the live relative paths ("rels") of its endpoints. This
module resolves the path templates hardcoded in :mod:`cookidoo_api.const` to
their live equivalents on a best-effort basis, so a renamed path segment can
be picked up automatically instead of silently breaking.

Only the services/rels actually consumed by this library are fetched (see
:data:`ENDPOINT_RELS`), not a full recursive crawl. This mapping is also the
single source of truth for narrowing the CI drift-check in
``scripts/well-known-discovery.py`` to the endpoints we actually use.
"""

from __future__ import annotations

import logging
import re
from typing import Final

from aiohttp import ClientError, ClientSession
from yarl import URL

from cookidoo_api.const import (
    ADD_ADDITIONAL_ITEMS_PATH,
    ADD_CUSTOM_COLLECTION_PATH,
    ADD_CUSTOM_RECIPE_PATH,
    ADD_INGREDIENT_ITEMS_FOR_RECIPES_PATH,
    ADD_MANAGED_COLLECTION_PATH,
    ADD_RECIPES_TO_CALENDER_PATH,
    ADD_RECIPES_TO_CUSTOM_COLLECTION_PATH,
    ADDITIONAL_ITEMS_PATH,
    COMMUNITY_PROFILE_PATH,
    CUSTOM_COLLECTIONS_PATH,
    CUSTOM_RECIPE_PATH,
    CUSTOM_RECIPES_PATH,
    EDIT_ADDITIONAL_ITEMS_PATH,
    EDIT_OWNERSHIP_ADDITIONAL_ITEMS_PATH,
    EDIT_OWNERSHIP_INGREDIENT_ITEMS_PATH,
    INGREDIENT_ITEMS_PATH,
    LOGIN_PATH,
    MANAGED_COLLECTIONS_PATH,
    RECIPE_PATH,
    RECIPES_IN_CALENDAR_WEEK_PATH,
    REMOVE_ADDITIONAL_ITEMS_PATH,
    REMOVE_CUSTOM_COLLECTION_PATH,
    REMOVE_CUSTOM_RECIPE_PATH,
    REMOVE_INGREDIENT_ITEMS_FOR_RECIPES_PATH,
    REMOVE_MANAGED_COLLECTION_PATH,
    REMOVE_RECIPE_FROM_CALENDER_PATH,
    REMOVE_RECIPE_FROM_CUSTOM_COLLECTION_PATH,
    SHOPPING_LIST_RECIPES_PATH,
    SUBSCRIPTIONS_PATH,
)

_LOGGER = logging.getLogger(__name__)

WELL_KNOWN_HOME_PATH: Final = ".well-known/home"

# Maps each path constant name (matching cookidoo_api.const) to the HAL
# service document and relation ("rel") that exposes its live equivalent, as
# crawled by scripts/well-known-discovery.py into
# well-known-snapshots/latest.json. Keep this in sync with that script's
# allow-list so the CI drift-check only watches endpoints we actually use.
ENDPOINT_RELS: Final[dict[str, tuple[str, str]]] = {
    "LOGIN_PATH": ("profile", "fint:login"),
    "RECIPE_PATH": ("recipes/recipe", "recipe:details"),
    "CUSTOM_RECIPES_PATH": ("created-recipes", "customer-recipes:recipe-create"),
    "ADD_CUSTOM_RECIPE_PATH": ("created-recipes", "customer-recipes:recipe-create"),
    "CUSTOM_RECIPE_PATH": ("created-recipes", "customer-recipes:recipe-details"),
    "REMOVE_CUSTOM_RECIPE_PATH": (
        "created-recipes",
        "customer-recipes:recipe-details",
    ),
    "COMMUNITY_PROFILE_PATH": (
        "community/profile",
        "community-profile:user-private-profile",
    ),
    "SUBSCRIPTIONS_PATH": ("ownership", "ownership:subscriptions"),
    "SHOPPING_LIST_RECIPES_PATH": ("shopping", "pantry:home"),
    "INGREDIENT_ITEMS_PATH": ("shopping", "pantry:home"),
    "ADDITIONAL_ITEMS_PATH": ("shopping", "pantry:home"),
    "EDIT_OWNERSHIP_INGREDIENT_ITEMS_PATH": (
        "shopping",
        "pantry:edit-ingredients-ownership",
    ),
    "ADD_INGREDIENT_ITEMS_FOR_RECIPES_PATH": ("shopping", "pantry:recipe-ingredients"),
    "REMOVE_INGREDIENT_ITEMS_FOR_RECIPES_PATH": ("shopping", "pantry:remove-recipe"),
    "ADD_ADDITIONAL_ITEMS_PATH": ("shopping", "pantry:add-additional-items-v2"),
    "EDIT_ADDITIONAL_ITEMS_PATH": ("shopping", "pantry:edit-additional-items"),
    "EDIT_OWNERSHIP_ADDITIONAL_ITEMS_PATH": (
        "shopping",
        "pantry:edit-additional-items-ownership",
    ),
    "REMOVE_ADDITIONAL_ITEMS_PATH": ("shopping", "pantry:remove-additional-items"),
    "CUSTOM_COLLECTIONS_PATH": ("organize", "organize:api-custom-list"),
    "ADD_CUSTOM_COLLECTION_PATH": ("organize", "organize:api-custom-list"),
    "REMOVE_CUSTOM_COLLECTION_PATH": ("organize", "organize:api-custom-list-modify"),
    "ADD_RECIPES_TO_CUSTOM_COLLECTION_PATH": (
        "organize",
        "organize:api-custom-list-modify",
    ),
    "REMOVE_RECIPE_FROM_CUSTOM_COLLECTION_PATH": (
        "organize",
        "organize:api-custom-list-recipe",
    ),
    "MANAGED_COLLECTIONS_PATH": ("organize", "organize:api-managed-list"),
    "ADD_MANAGED_COLLECTION_PATH": ("organize", "organize:api-managed-list"),
    "REMOVE_MANAGED_COLLECTION_PATH": (
        "organize",
        "organize:api-managed-list-single",
    ),
    "RECIPES_IN_CALENDAR_WEEK_PATH": ("planning", "planning:api-my-week-from-date"),
    "ADD_RECIPES_TO_CALENDER_PATH": ("planning", "planning:api-my-day"),
    "REMOVE_RECIPE_FROM_CALENDER_PATH": ("planning", "planning:api-my-day-recipes"),
}

# Hardcoded defaults, used both as the fallback when discovery fails/mismatches
# and as the reference shape (number/order of {placeholders}) that a
# discovered href is normalized against.
_ENDPOINT_DEFAULTS: Final[dict[str, str]] = {
    "LOGIN_PATH": LOGIN_PATH,
    "RECIPE_PATH": RECIPE_PATH,
    "CUSTOM_RECIPES_PATH": CUSTOM_RECIPES_PATH,
    "ADD_CUSTOM_RECIPE_PATH": ADD_CUSTOM_RECIPE_PATH,
    "CUSTOM_RECIPE_PATH": CUSTOM_RECIPE_PATH,
    "REMOVE_CUSTOM_RECIPE_PATH": REMOVE_CUSTOM_RECIPE_PATH,
    "COMMUNITY_PROFILE_PATH": COMMUNITY_PROFILE_PATH,
    "SUBSCRIPTIONS_PATH": SUBSCRIPTIONS_PATH,
    "SHOPPING_LIST_RECIPES_PATH": SHOPPING_LIST_RECIPES_PATH,
    "INGREDIENT_ITEMS_PATH": INGREDIENT_ITEMS_PATH,
    "ADDITIONAL_ITEMS_PATH": ADDITIONAL_ITEMS_PATH,
    "EDIT_OWNERSHIP_INGREDIENT_ITEMS_PATH": EDIT_OWNERSHIP_INGREDIENT_ITEMS_PATH,
    "ADD_INGREDIENT_ITEMS_FOR_RECIPES_PATH": ADD_INGREDIENT_ITEMS_FOR_RECIPES_PATH,
    "REMOVE_INGREDIENT_ITEMS_FOR_RECIPES_PATH": REMOVE_INGREDIENT_ITEMS_FOR_RECIPES_PATH,
    "ADD_ADDITIONAL_ITEMS_PATH": ADD_ADDITIONAL_ITEMS_PATH,
    "EDIT_ADDITIONAL_ITEMS_PATH": EDIT_ADDITIONAL_ITEMS_PATH,
    "EDIT_OWNERSHIP_ADDITIONAL_ITEMS_PATH": EDIT_OWNERSHIP_ADDITIONAL_ITEMS_PATH,
    "REMOVE_ADDITIONAL_ITEMS_PATH": REMOVE_ADDITIONAL_ITEMS_PATH,
    "CUSTOM_COLLECTIONS_PATH": CUSTOM_COLLECTIONS_PATH,
    "ADD_CUSTOM_COLLECTION_PATH": ADD_CUSTOM_COLLECTION_PATH,
    "REMOVE_CUSTOM_COLLECTION_PATH": REMOVE_CUSTOM_COLLECTION_PATH,
    "ADD_RECIPES_TO_CUSTOM_COLLECTION_PATH": ADD_RECIPES_TO_CUSTOM_COLLECTION_PATH,
    "REMOVE_RECIPE_FROM_CUSTOM_COLLECTION_PATH": REMOVE_RECIPE_FROM_CUSTOM_COLLECTION_PATH,
    "MANAGED_COLLECTIONS_PATH": MANAGED_COLLECTIONS_PATH,
    "ADD_MANAGED_COLLECTION_PATH": ADD_MANAGED_COLLECTION_PATH,
    "REMOVE_MANAGED_COLLECTION_PATH": REMOVE_MANAGED_COLLECTION_PATH,
    "RECIPES_IN_CALENDAR_WEEK_PATH": RECIPES_IN_CALENDAR_WEEK_PATH,
    "ADD_RECIPES_TO_CALENDER_PATH": ADD_RECIPES_TO_CALENDER_PATH,
    "REMOVE_RECIPE_FROM_CALENDER_PATH": REMOVE_RECIPE_FROM_CALENDER_PATH,
}

_DOMAIN_PREFIX_RE = re.compile(r"^https?://[^/]+")
_QUERY_SUFFIX_RE = re.compile(r"\{[?&].*$")
_TOKEN_RE = re.compile(r"(\{/?)([A-Za-z0-9_]+)(\})")


def _normalize_href(href: str, const_template: str) -> str | None:
    """Normalize a discovered HAL href into our const.py template shape.

    The discovered ``href`` may be absolute (with scheme/host), may carry a
    trailing RFC 6570 query template (``{?a,b}``), and uses variable names
    that differ from ours (e.g. ``{lang}``/``{dayKey}`` instead of
    ``{language}``/``{day}``). We keep the *literal* path segments from the
    live document (so a renamed segment is picked up automatically) but
    always substitute our own variable names, positionally, so existing
    ``.format(language=..., id=...)`` call sites elsewhere keep working
    unchanged.

    Returns ``None`` (signalling the caller to keep the hardcoded default)
    if the number of variables doesn't match, since that indicates a shape
    change too significant to reconcile automatically.
    """
    path = _DOMAIN_PREFIX_RE.sub("", href)
    path = _QUERY_SUFFIX_RE.sub("", path)

    our_tokens = [m.group(2) for m in _TOKEN_RE.finditer(const_template)]
    discovered_tokens = list(_TOKEN_RE.finditer(path))
    if len(our_tokens) != len(discovered_tokens):
        return None

    it = iter(our_tokens)

    def _replace(match: re.Match[str]) -> str:
        prefix = "/" if match.group(1) == "{/" else ""
        return f"{prefix}{{{next(it)}}}"

    normalized = _TOKEN_RE.sub(_replace, path)
    return normalized.lstrip("/")


async def _fetch_service_links(
    session: ClientSession, service_url: URL
) -> dict[str, str] | None:
    """Fetch a single ``.well-known/home`` HAL document's rel -> href links."""
    try:
        async with session.get(service_url) as resp:
            if resp.status != 200:
                _LOGGER.debug(
                    "Well-known discovery: %s returned status %s, skipping.",
                    service_url,
                    resp.status,
                )
                return None
            doc = await resp.json(content_type=None)
    except (ClientError, TimeoutError, ValueError) as e:
        _LOGGER.debug("Well-known discovery failed for %s: %s", service_url, e)
        return None

    links = doc.get("_links") if isinstance(doc, dict) else None
    if not isinstance(links, dict):
        return None

    result: dict[str, str] = {}
    for rel, value in links.items():
        href: object = None
        if isinstance(value, dict):
            href = value.get("href")
        elif isinstance(value, list) and value and isinstance(value[0], dict):
            href = value[0].get("href")
        if isinstance(href, str):
            result[rel] = href
    return result


async def resolve_endpoint_paths(
    session: ClientSession, api_endpoint: URL
) -> dict[str, str]:
    """Resolve live endpoint path templates via ``.well-known/home`` discovery.

    Fetches only the services referenced in :data:`ENDPOINT_RELS` (not a full
    recursive crawl), extracts only the rels we use, and normalizes them into
    our template shape.

    Parameters
    ----------
    session
        The client session for aiohttp requests.
    api_endpoint
        The Cookidoo domain root (e.g. ``https://cookidoo.ch``) to resolve
        service discovery documents against.

    Returns
    -------
    dict[str, str]
        A mapping of constant name -> discovered path template, for every
        constant that was successfully resolved. Constants that fail to
        resolve (network error, missing rel, or an incompatible shape
        change) are simply absent; callers should fall back to their
        hardcoded default (:mod:`cookidoo_api.const`) in that case. This
        function never raises: discovery is a best-effort robustness
        improvement, not a hard requirement, since the hardcoded fallback
        always keeps the library functional even if Cookidoo's discovery
        document is unreachable.

    """
    services = {service for service, _rel in ENDPOINT_RELS.values()}
    service_links: dict[str, dict[str, str] | None] = {}
    for service in services:
        service_url = api_endpoint / service / WELL_KNOWN_HOME_PATH
        service_links[service] = await _fetch_service_links(session, service_url)

    overrides: dict[str, str] = {}
    for name, (service, rel) in ENDPOINT_RELS.items():
        links = service_links.get(service)
        if not links or rel not in links:
            continue
        normalized = _normalize_href(links[rel], _ENDPOINT_DEFAULTS[name])
        if normalized is not None:
            overrides[name] = normalized
        else:
            _LOGGER.debug(
                "Well-known discovery: shape mismatch for %s (rel %s), "
                "keeping hardcoded default.",
                name,
                rel,
            )
    return overrides
