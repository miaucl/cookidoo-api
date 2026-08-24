"""Unit tests for the .well-known/home endpoint discovery module."""

from aiohttp import ClientSession
from aioresponses import aioresponses
import pytest
from yarl import URL

from cookidoo_api.well_known import (
    _ENDPOINT_DEFAULTS,
    ENDPOINT_RELS,
    _fetch_service_links,
    _normalize_href,
    resolve_endpoint_paths,
)

API_ENDPOINT = URL("https://cookidoo.ch")


def test_endpoint_rels_have_matching_defaults() -> None:
    """Every configured rel must have a matching hardcoded default template."""
    assert set(ENDPOINT_RELS) == set(_ENDPOINT_DEFAULTS)


@pytest.mark.parametrize(
    ("href", "const_template", "expected"),
    [
        # Absolute href, plain {var} tokens.
        (
            "https://de.web.production-eu.cookidoo.vorwerk-digital.com/planning/{lang}/api/my-week/{dayKey}",
            "planning/{language}/api/my-week/{day}",
            "planning/{language}/api/my-week/{day}",
        ),
        # Relative href with a trailing RFC 6570 query template to strip.
        (
            "/profile/{lang}/login{?redirectAfterLogin}",
            "profile/{language}/login",
            "profile/{language}/login",
        ),
        # RFC 6570 path-segment token ({/lang}) must keep its separating slash.
        (
            "https://de.web.production-eu.cookidoo.vorwerk-digital.com/recipes/recipe{/lang}/{id}",
            "recipes/recipe/{language}/{id}",
            "recipes/recipe/{language}/{id}",
        ),
        # No placeholders on either side.
        (
            "https://de.web.production-eu.cookidoo.vorwerk-digital.com/ownership/subscriptions",
            "ownership/subscriptions",
            "ownership/subscriptions",
        ),
    ],
)
def test_normalize_href_success(href: str, const_template: str, expected: str) -> None:
    """Discovered hrefs are normalized into our const.py template shape."""
    assert _normalize_href(href, const_template) == expected


def test_normalize_href_shape_mismatch_returns_none() -> None:
    """A different number of variables signals an incompatible shape change."""
    assert (
        _normalize_href(
            "https://de.web.production-eu.cookidoo.vorwerk-digital.com/community/profile/{lang}",
            "community/profile",
        )
        is None
    )


async def test_fetch_service_links_success(
    session: ClientSession, mocked: aioresponses
) -> None:
    """A well-formed HAL document is parsed into a rel -> href mapping."""
    service_url = API_ENDPOINT / "shopping/.well-known/home"
    mocked.get(
        service_url,
        payload={
            "_links": {
                "pantry:home": {"href": "/shopping/{lang}"},
                "pantry:list-variant": [
                    {"href": "/shopping/{lang}/a"},
                    {"href": "/shopping/{lang}/b"},
                ],
                "pantry:broken": {"notAnHref": True},
                "pantry:empty-list": [],
                "pantry:weird": 123,
            }
        },
    )
    links = await _fetch_service_links(session, service_url)
    assert links == {
        "pantry:home": "/shopping/{lang}",
        "pantry:list-variant": "/shopping/{lang}/a",
    }


async def test_fetch_service_links_non_200(
    session: ClientSession, mocked: aioresponses
) -> None:
    """A non-200 response is treated as unavailable, not an error."""
    service_url = API_ENDPOINT / "shopping/.well-known/home"
    mocked.get(service_url, status=404)
    assert await _fetch_service_links(session, service_url) is None


async def test_fetch_service_links_connection_error(
    session: ClientSession, mocked: aioresponses
) -> None:
    """A connection failure is swallowed and treated as unavailable."""
    service_url = API_ENDPOINT / "shopping/.well-known/home"
    # No mock registered for this URL: aioresponses raises a ClientConnectionError.
    assert await _fetch_service_links(session, service_url) is None


async def test_fetch_service_links_invalid_json(
    session: ClientSession, mocked: aioresponses
) -> None:
    """A response that isn't a JSON object is treated as unavailable."""
    service_url = API_ENDPOINT / "shopping/.well-known/home"
    mocked.get(service_url, body="not json", content_type="application/json")
    assert await _fetch_service_links(session, service_url) is None


async def test_fetch_service_links_no_links_key(
    session: ClientSession, mocked: aioresponses
) -> None:
    """A JSON object without a `_links` mapping is treated as unavailable."""
    service_url = API_ENDPOINT / "shopping/.well-known/home"
    mocked.get(service_url, payload={"meta": {}})
    assert await _fetch_service_links(session, service_url) is None


async def test_resolve_endpoint_paths_mixed_results(
    session: ClientSession, mocked: aioresponses
) -> None:
    """Discovery mixes successful overrides, mismatches, and fallbacks gracefully."""
    for service in {service for service, _rel in ENDPOINT_RELS.values()}:
        service_url = API_ENDPOINT / service / ".well-known/home"
        if service == "profile":
            mocked.get(
                service_url,
                payload={
                    "_links": {
                        "fint:login": {
                            "href": "/profile/{lang}/login{?redirectAfterLogin}"
                        }
                    }
                },
            )
        elif service == "community/profile":
            # Shape mismatch: our const has no placeholder, discovery adds one.
            mocked.get(
                service_url,
                payload={
                    "_links": {
                        "community-profile:user-private-profile": {
                            "href": "https://de.web.production-eu.cookidoo.vorwerk-digital.com/community/profile/{lang}"
                        }
                    }
                },
            )
        else:
            mocked.get(service_url, status=404)

    overrides = await resolve_endpoint_paths(session, API_ENDPOINT)

    assert overrides["LOGIN_PATH"] == "profile/{language}/login"
    assert "COMMUNITY_PROFILE_PATH" not in overrides
    assert "RECIPE_PATH" not in overrides
