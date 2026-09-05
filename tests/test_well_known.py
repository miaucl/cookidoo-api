"""Unit tests for the .well-known/home endpoint discovery module."""

from aiohttp import ClientSession
from aioresponses import aioresponses
import pytest
from yarl import URL

from cookidoo_api.exceptions import CookidooParseException, CookidooRequestException
from cookidoo_api.well_known import (
    _TOKEN_RE,
    ENDPOINT_RELS,
    _fetch_service_links,
    _normalize_href,
    resolve_endpoint_paths,
)

API_ENDPOINT = URL("https://cookidoo.ch")


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
        # Absolute href with a single {var} token plus a trailing RFC 6570
        # query template to strip (search:home).
        (
            "https://de.web.production-eu.cookidoo.vorwerk-digital.com/search/{lang}{?query,context,filters*,focus,pagination,limit}",
            "search/{locale}",
            "search/{locale}",
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


def test_normalize_href_known_token_reorder_returns_none() -> None:
    """A known-name token in the wrong position signals a silent reorder."""
    # {dayKey}/{recipeId} swapped relative to our {recipe}/{day}: same count,
    # both names recognized, but lined up against the wrong our-name.
    assert (
        _normalize_href(
            "https://de.web.production-eu.cookidoo.vorwerk-digital.com/planning/{lang}/api/my-day/{recipeId}/recipes/{dayKey}",
            "planning/{language}/api/my-day/{day}/recipes/{recipe}",
        )
        is None
    )


def test_normalize_href_unknown_token_falls_back_to_positional() -> None:
    """A token name we don't recognize still substitutes positionally."""
    assert (
        _normalize_href(
            "https://de.web.production-eu.cookidoo.vorwerk-digital.com/ownership/{someNewToken}",
            "ownership/{language}",
        )
        == "ownership/{language}"
    )


async def test_fetch_service_links_sends_discovery_headers(
    session: ClientSession, mocked: aioresponses
) -> None:
    """Discovery GETs carry a browser User-Agent to avoid Cloudflare bot-filtering."""
    service_url = API_ENDPOINT / "shopping/.well-known/home"
    mocked.get(service_url, payload={"_links": {}})

    await _fetch_service_links(session, service_url)

    request = next(iter(mocked.requests.values()))[0]
    sent_headers = request.kwargs["headers"]
    assert sent_headers["ACCEPT"] == "application/json"
    assert "Mozilla" in sent_headers["User-Agent"]


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


def _mock_all_services(
    mocked: aioresponses, overrides: dict[str, dict[str, object]] | None = None
) -> None:
    """Mock every service's .well-known/home with a valid response for every rel.

    ``overrides`` can replace individual service mocks (e.g. with a 404, or a
    payload missing/mismatching a specific rel) by service name.
    """
    overrides = overrides or {}
    rels_by_service: dict[str, list[str]] = {}
    for rel, (service, _template) in ENDPOINT_RELS.items():
        rels_by_service.setdefault(service, []).append(rel)

    for service, rels in rels_by_service.items():
        service_url = API_ENDPOINT / service / ".well-known/home"
        if service in overrides:
            mocked.get(service_url, **overrides[service])
            continue
        links = {}
        for rel in rels:
            _, template = ENDPOINT_RELS[rel]
            placeholder_count = len(_TOKEN_RE.findall(template))
            tokens = "".join(f"/{{var{i}}}" for i in range(placeholder_count))
            links[rel] = {"href": f"/{service}{tokens}"}
        mocked.get(service_url, payload={"_links": links})


async def test_resolve_endpoint_paths_success(
    session: ClientSession, mocked: aioresponses
) -> None:
    """Every rel resolves successfully, returning a full overrides mapping."""
    _mock_all_services(mocked)

    overrides = await resolve_endpoint_paths(session, API_ENDPOINT)

    assert set(overrides) == set(ENDPOINT_RELS)
    assert overrides["recipe:details"] == "recipes/recipe/{language}/{id}"


async def test_resolve_endpoint_paths_unreachable_service_raises(
    session: ClientSession, mocked: aioresponses
) -> None:
    """An unreachable service raises CookidooRequestException."""
    _mock_all_services(mocked, {"ownership": {"status": 404}})

    with pytest.raises(CookidooRequestException):
        await resolve_endpoint_paths(session, API_ENDPOINT)


async def test_resolve_endpoint_paths_reachable_but_no_usable_links_raises_parse_error(
    session: ClientSession, mocked: aioresponses
) -> None:
    """A reachable service with no usable hrefs is a parse error, not a request one.

    ``_fetch_service_links`` returns an empty (not ``None``) dict when the
    document parsed fine but no link had a usable string href -- that's a
    shape problem, and mustn't be misreported as "could not reach the
    service" (which callers, incl. the retry-once logic, may treat as more
    likely to be transient).
    """
    _mock_all_services(
        mocked, {"ownership": {"payload": {"_links": {"broken": {"notAnHref": True}}}}}
    )

    with pytest.raises(CookidooParseException):
        await resolve_endpoint_paths(session, API_ENDPOINT)


async def test_resolve_endpoint_paths_missing_rel_raises(
    session: ClientSession, mocked: aioresponses
) -> None:
    """A service reachable but no longer exposing our rel raises a parse error."""
    _mock_all_services(
        mocked,
        {"ownership": {"payload": {"_links": {"other:rel": {"href": "/x"}}}}},
    )

    with pytest.raises(CookidooParseException):
        await resolve_endpoint_paths(session, API_ENDPOINT)


async def test_resolve_endpoint_paths_shape_mismatch_raises(
    session: ClientSession, mocked: aioresponses
) -> None:
    """A discovered href with an incompatible shape raises a parse error."""
    _mock_all_services(
        mocked,
        {
            "community/profile": {
                "payload": {
                    "_links": {
                        "community-profile:user-private-profile": {
                            "href": "https://de.web.production-eu.cookidoo.vorwerk-digital.com/community/profile"
                        }
                    }
                }
            }
        },
    )

    with pytest.raises(CookidooParseException):
        await resolve_endpoint_paths(session, API_ENDPOINT)
