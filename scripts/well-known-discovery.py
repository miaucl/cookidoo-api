#!/usr/bin/env python3
"""Crawl and snapshot the Cookidoo `.well-known/home` endpoints we depend on.

Unlike a full recursive crawl of every Cookidoo microservice, this only
fetches the services/rels listed in ``cookidoo_api.well_known.ENDPOINT_RELS``
-- the same allow-list the library itself uses at runtime to resolve its
path templates -- plus a small number of rels in :data:`WATCH_ONLY_RELS`
that the library doesn't call but still wants a heads-up on. This keeps the
drift-check (and the PRs it opens) scoped to endpoints cookidoo-api cares
about, instead of firing on unrelated changes anywhere in Cookidoo's ~27
microservices.
"""

import json
from pathlib import Path
import sys

import requests

from cookidoo_api.const import LOGIN_PATH
from cookidoo_api.well_known import ENDPOINT_RELS

API_ENDPOINT = "https://cookidoo.de"
OUT_DIR = Path("well-known-snapshots")
TIMEOUT = 10

# Rels the drift-check watches for a heads-up even though the library has
# no runtime call site for them (see well_known.ENDPOINT_RELS' docstring
# for why: resolve_endpoint_paths() is all-or-nothing, so an endpoint we
# don't actually call can't live in that runtime allow-list without making
# every API call depend on it). Declared in the same
# ``rel -> (service, shape_template)`` shape so they're handled identically
# by crawl()/diff_links(), just merged in separately from the runtime one.
WATCH_ONLY_RELS: dict[str, tuple[str, str]] = {
    "fint:login": ("profile", LOGIN_PATH),
}


def fetch_json(url: str) -> dict:
    """Fetch JSON document from URL."""
    r = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": "python/requests"})
    r.raise_for_status()
    result: dict = r.json()
    return result


def crawl(old_snapshot: dict) -> dict:
    """Fetch the services/rels declared in ENDPOINT_RELS and WATCH_ONLY_RELS.

    Returns a flat mapping of ``"{rel} ({service})" -> href`` for every rel
    we could resolve, plus an ``"_errors"`` bookkeeping entry listing
    services that couldn't be fetched at all (not treated as an endpoint
    change by itself, see :func:`diff_links`).

    When a service's fetch fails, that service's rels are carried over
    verbatim from ``old_snapshot`` instead of being dropped: a transient
    outage must not make every one of that service's rels look "removed"
    (and, once the service recovers, "added" again) to :func:`diff_links`.
    """
    all_rels = {**ENDPOINT_RELS, **WATCH_ONLY_RELS}
    services = sorted({service for service, _template in all_rels.values()})
    service_links: dict[str, dict] = {}
    errors: dict[str, str] = {}

    for service in services:
        url = f"{API_ENDPOINT}/{service}/.well-known/home"
        print(f"Fetching {url}")
        try:
            doc = fetch_json(url)
        except Exception as e:  # noqa: BLE001
            errors[service] = str(e)
            continue
        service_links[service] = doc.get("_links", {})

    result: dict[str, object] = {}
    for rel, (service, _template) in sorted(all_rels.items()):
        key = f"{rel} ({service})"
        if service in errors:
            if key in old_snapshot:
                result[key] = old_snapshot[key]
            continue
        links = service_links.get(service)
        if links is None:
            continue
        value = links.get(rel)
        if isinstance(value, dict):
            href = value.get("href")
        elif isinstance(value, list) and value and isinstance(value[0], dict):
            href = value[0].get("href")
        else:
            href = None
        result[key] = href

    if errors:
        result["_errors"] = errors

    return result


def write_snapshot(data: dict) -> None:
    """Write the snapshot to disk."""
    OUT_DIR.mkdir(exist_ok=True)
    latest = OUT_DIR / "latest.json"
    latest.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    print("Snapshot updated.")


def diff_links(old: dict, new: dict) -> dict:
    """Diff two name -> href mappings (ignoring the `_errors` bookkeeping key).

    Transient fetch failures (which only affect ``_errors``) are not
    considered a meaningful, actionable change on their own.
    """
    old = {k: v for k, v in old.items() if k != "_errors"}
    new = {k: v for k, v in new.items() if k != "_errors"}

    old_keys = set(old.keys())
    new_keys = set(new.keys())

    added = sorted(new_keys - old_keys)
    removed = sorted(old_keys - new_keys)
    changed = sorted(k for k in old_keys & new_keys if old[k] != new[k])

    return {"added": added, "removed": removed, "changed": changed}


def main() -> None:
    """Crawl and snapshot the used well-known endpoints."""
    latest_path = OUT_DIR / "latest.json"
    is_first_run = not latest_path.exists()
    old_snapshot = json.loads(latest_path.read_text()) if not is_first_run else {}

    snapshot = crawl(old_snapshot)

    diff = diff_links(old_snapshot, snapshot)
    Path("diff-summary.json").write_text(json.dumps(diff, indent=2), encoding="utf-8")

    meaningful_change = bool(diff["added"] or diff["removed"] or diff["changed"])

    # Only rewrite (and thus git-diff) the snapshot file when one of our used
    # endpoints actually changed, or on the very first run. A snapshot
    # rewrite caused solely by `_errors` fluctuating (a transient outage)
    # must not by itself trigger a PR.
    if meaningful_change or is_first_run:
        write_snapshot(snapshot)
    else:
        print("No changes detected.")

    sys.exit(1 if meaningful_change else 0)


if __name__ == "__main__":
    main()
