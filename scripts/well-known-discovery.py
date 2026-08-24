#!/usr/bin/env python3
"""Crawl and snapshot the Cookidoo `.well-known/home` endpoints we depend on.

Unlike a full recursive crawl of every Cookidoo microservice, this only
fetches the services/rels listed in ``cookidoo_api.well_known.ENDPOINT_RELS``
-- the same allow-list the library itself uses at runtime to resolve its
path templates. This keeps the drift-check (and the PRs it opens) scoped to
endpoints cookidoo-api actually consumes, instead of firing on unrelated
changes anywhere in Cookidoo's ~27 microservices.
"""

import json
from pathlib import Path
import sys

import requests

from cookidoo_api.well_known import ENDPOINT_RELS

API_ENDPOINT = "https://cookidoo.de"
OUT_DIR = Path("well-known-snapshots")
TIMEOUT = 10


def fetch_json(url: str) -> dict:
    """Fetch JSON document from URL."""
    r = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": "python/requests"})
    r.raise_for_status()
    result: dict = r.json()
    return result


def crawl() -> dict:
    """Fetch only the services/rels declared in ENDPOINT_RELS.

    Returns a flat mapping of ``"{name} ({service}#{rel})" -> href`` for
    every constant we could resolve, plus an ``"_errors"`` bookkeeping entry
    listing services that couldn't be fetched at all (not treated as an
    endpoint change by itself, see :func:`diff_links`).
    """
    services = sorted({service for service, _rel in ENDPOINT_RELS.values()})
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
    for name, (service, rel) in sorted(ENDPOINT_RELS.items()):
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
        result[f"{name} ({service}#{rel})"] = href

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
    snapshot = crawl()

    latest_path = OUT_DIR / "latest.json"
    is_first_run = not latest_path.exists()
    old_snapshot = json.loads(latest_path.read_text()) if not is_first_run else {}

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
