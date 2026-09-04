"""Discovery of Cookidoo API endpoints via the ``.well-known/home`` HAL documents.

Cookidoo's backend exposes a `HAL <https://en.wikipedia.org/wiki/Hypertext_Application_Language>`_
``.well-known/home`` document per microservice (e.g. ``shopping``, ``planning``,
``organize``), listing the live relative paths ("rels") of its endpoints. This
module resolves the live path template for every rel this library depends on.
There is no hardcoded fallback: a rel that can't be resolved (network error,
or a shape too different to reconcile) fails the request instead of silently
serving a possibly-stale path.

Only the services/rels actually consumed by this library are fetched (see
:data:`ENDPOINT_RELS`), not a full recursive crawl. This mapping is also the
single source of truth for narrowing the CI drift-check in
``scripts/well-known-discovery.py`` to the endpoints we actually use.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Final

from aiohttp import ClientError, ClientSession
from yarl import URL

from cookidoo_api.const import (
    ADD_ADDITIONAL_ITEMS_PATH,
    ADD_INGREDIENT_ITEMS_FOR_RECIPES_PATH,
    ADD_RECIPES_TO_CALENDER_PATH,
    COMMUNITY_PROFILE_PATH,
    CUSTOM_COLLECTIONS_PATH,
    CUSTOM_RECIPE_PATH,
    CUSTOM_RECIPES_PATH,
    DEFAULT_API_HEADERS,
    DEVICES_PATH,
    EDIT_ADDITIONAL_ITEMS_PATH,
    EDIT_OWNERSHIP_ADDITIONAL_ITEMS_PATH,
    EDIT_OWNERSHIP_INGREDIENT_ITEMS_PATH,
    LOGIN_HEADERS,
    MANAGED_COLLECTIONS_PATH,
    RECIPE_PATH,
    RECIPES_IN_CALENDAR_WEEK_PATH,
    REMOVE_ADDITIONAL_ITEMS_PATH,
    REMOVE_CUSTOM_COLLECTION_PATH,
    REMOVE_INGREDIENT_ITEMS_FOR_RECIPES_PATH,
    REMOVE_MANAGED_COLLECTION_PATH,
    REMOVE_RECIPE_FROM_CALENDER_PATH,
    REMOVE_RECIPE_FROM_CUSTOM_COLLECTION_PATH,
    SEARCH_PATH,
    SHOPPING_LIST_RECIPES_PATH,
    SUBSCRIPTIONS_PATH,
)
from cookidoo_api.exceptions import CookidooParseException, CookidooRequestException

_LOGGER = logging.getLogger(__name__)

WELL_KNOWN_HOME_PATH: Final = ".well-known/home"

# Sent with every discovery request. The login flow's own Cloudflare-bot
# hazard (see LOGIN_HEADERS/const.py, issue #230) applies just as much
# here: these are unauthenticated GETs against the same cookidoo.* domain,
# and since there is no hardcoded fallback, a 403 here is a total outage
# for every method of the client, not just degraded behaviour.
_DISCOVERY_HEADERS: Final = {**DEFAULT_API_HEADERS, **LOGIN_HEADERS}


# Maps each well-known "rel" this library depends on to the HAL service
# document exposing it and the shape (placeholder names, matching our
# `.format(language=..., id=...)` call sites) a discovered href is
# normalized against. The rel itself is the lookup key everywhere else
# (Cookidoo._path(rel)), so a rel backing more than one call site (e.g.
# ``pantry:home`` is shared by the shopping list, ingredient items, and
# additional items screens) is declared once here, not once per caller.
#
# Only rels actually resolved via _path() belong here: resolve_endpoint_paths()
# is all-or-nothing, so an extra unused rel would make every API call
# depend on a service/rel the library never calls (e.g. ``fint:login``,
# which login() never uses since auth goes through the OAuth2/CIAM flow,
# not this HAL document -- that one is instead watched separately by
# scripts/well-known-discovery.py's drift-check, since we still want a
# heads-up if it disappears, without it being a hard runtime dependency).
# Keep this in sync with scripts/well-known-discovery.py's own allow-list.
ENDPOINT_RELS: Final[dict[str, tuple[str, str]]] = {
    "recipe:details": ("recipes/recipe", RECIPE_PATH),
    "customer-recipes:recipe-create": ("created-recipes", CUSTOM_RECIPES_PATH),
    "customer-recipes:recipe-details": ("created-recipes", CUSTOM_RECIPE_PATH),
    "community-profile:user-private-profile": (
        "community/profile",
        COMMUNITY_PROFILE_PATH,
    ),
    "ownership:subscriptions": ("ownership", SUBSCRIPTIONS_PATH),
    "pantry:home": ("shopping", SHOPPING_LIST_RECIPES_PATH),
    "pantry:edit-ingredients-ownership": (
        "shopping",
        EDIT_OWNERSHIP_INGREDIENT_ITEMS_PATH,
    ),
    "pantry:recipe-ingredients": ("shopping", ADD_INGREDIENT_ITEMS_FOR_RECIPES_PATH),
    "pantry:remove-recipe": ("shopping", REMOVE_INGREDIENT_ITEMS_FOR_RECIPES_PATH),
    "pantry:add-additional-items-v2": ("shopping", ADD_ADDITIONAL_ITEMS_PATH),
    "pantry:edit-additional-items": ("shopping", EDIT_ADDITIONAL_ITEMS_PATH),
    "pantry:edit-additional-items-ownership": (
        "shopping",
        EDIT_OWNERSHIP_ADDITIONAL_ITEMS_PATH,
    ),
    "pantry:remove-additional-items": ("shopping", REMOVE_ADDITIONAL_ITEMS_PATH),
    "organize:api-custom-list": ("organize", CUSTOM_COLLECTIONS_PATH),
    "organize:api-custom-list-modify": ("organize", REMOVE_CUSTOM_COLLECTION_PATH),
    "organize:api-custom-list-recipe": (
        "organize",
        REMOVE_RECIPE_FROM_CUSTOM_COLLECTION_PATH,
    ),
    "organize:api-managed-list": ("organize", MANAGED_COLLECTIONS_PATH),
    "organize:api-managed-list-single": ("organize", REMOVE_MANAGED_COLLECTION_PATH),
    "planning:api-my-week-from-date": ("planning", RECIPES_IN_CALENDAR_WEEK_PATH),
    "planning:api-my-day": ("planning", ADD_RECIPES_TO_CALENDER_PATH),
    "planning:api-my-day-recipes": ("planning", REMOVE_RECIPE_FROM_CALENDER_PATH),
    "customer-devices:thermomix-versions": ("customer-devices", DEVICES_PATH),
    "search:home": ("search", SEARCH_PATH),
}

_DOMAIN_PREFIX_RE = re.compile(r"^https?://[^/]+")
_QUERY_SUFFIX_RE = re.compile(r"\{[?&].*$")
_TOKEN_RE = re.compile(r"(\{/?)([A-Za-z0-9_]+)(\})")

# Cookidoo's own token names, as observed live, mapped to the set of our
# names they may legitimately stand for (``lang`` backs both our
# ``language`` and, for the search endpoint, ``locale``). A discovered
# token whose name is in here MUST line up (at its position) with one of
# these our-names, or normalization fails -- this catches a silent
# reordering (e.g. two same-shaped placeholders swapped) that a purely
# positional substitution would otherwise wave through. A discovered token
# whose name we don't recognize at all falls back to positional
# substitution, on the assumption it's simply a token Cookidoo hasn't
# renamed since we last looked.
_KNOWN_TOKEN_ALIASES: Final[dict[str, frozenset[str]]] = {
    "lang": frozenset({"language", "locale"}),
    "id": frozenset({"id"}),
    "dayKey": frozenset({"day"}),
    "recipeId": frozenset({"recipe"}),
}


def _normalize_href(href: str, shape_template: str) -> str | None:
    """Normalize a discovered HAL href into our own template shape.

    The discovered ``href`` may be absolute (with scheme/host), may carry a
    trailing RFC 6570 query template (``{?a,b}``), and uses variable names
    that differ from ours (e.g. ``{lang}``/``{dayKey}`` instead of
    ``{language}``/``{day}``). We keep the *literal* path segments from the
    live document (so a renamed segment is picked up automatically) but
    always substitute our own variable names, so existing
    ``.format(language=..., id=...)`` call sites elsewhere keep working
    unchanged. A token we recognize (see :data:`_KNOWN_TOKEN_ALIASES`) must
    line up with one of our expected names at that position; an unknown
    token name falls back to positional substitution.

    Returns ``None`` if the number of variables doesn't match, or a known
    token's position doesn't match one of its expected names, since that
    indicates a shape/order change too significant to reconcile
    automatically.
    """
    path = _DOMAIN_PREFIX_RE.sub("", href)
    path = _QUERY_SUFFIX_RE.sub("", path)

    our_tokens = [m.group(2) for m in _TOKEN_RE.finditer(shape_template)]
    discovered_tokens = [m.group(2) for m in _TOKEN_RE.finditer(path)]
    if len(our_tokens) != len(discovered_tokens):
        return None

    for discovered_name, our_name in zip(discovered_tokens, our_tokens, strict=True):
        expected = _KNOWN_TOKEN_ALIASES.get(discovered_name)
        if expected is not None and our_name not in expected:
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
        async with session.get(service_url, headers=_DISCOVERY_HEADERS) as resp:
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
    recursive crawl, and concurrently rather than one at a time), extracts
    only the rels we use, and normalizes them into our template shape.

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
        A mapping of rel -> discovered path template, for every rel in
        :data:`ENDPOINT_RELS`. Only returned once every single one resolved
        successfully; otherwise this function raises instead (there is no
        partial/hardcoded fallback).

    Raises
    ------
    CookidooRequestException
        If a service's ``.well-known/home`` document could not be reached.
    CookidooParseException
        If a rel is missing from its service document, or its discovered
        href's shape can't be reconciled with ours.

    """
    services = sorted({service for service, _shape in ENDPOINT_RELS.values()})
    fetched = await asyncio.gather(
        *(
            _fetch_service_links(session, api_endpoint / service / WELL_KNOWN_HOME_PATH)
            for service in services
        )
    )
    service_links: dict[str, dict[str, str] | None] = dict(
        zip(services, fetched, strict=True)
    )

    overrides: dict[str, str] = {}
    for rel, (service, shape_template) in ENDPOINT_RELS.items():
        links = service_links.get(service)
        if links is None:
            raise CookidooRequestException(
                f"Endpoint discovery failed: could not reach the '{service}' "
                f"service's .well-known/home document (needed to resolve "
                f"'{rel}')."
            )
        if rel not in links:
            raise CookidooParseException(
                f"Endpoint discovery failed: the '{service}' service's "
                f".well-known/home document no longer exposes the '{rel}' "
                f"relation."
            )
        normalized = _normalize_href(links[rel], shape_template)
        if normalized is None:
            raise CookidooParseException(
                f"Endpoint discovery failed: the '{rel}' relation on the "
                f"'{service}' service changed shape unexpectedly."
            )
        overrides[rel] = normalized
    return overrides
