#!/usr/bin/env python3
"""Crawl and snapshot the .well-known home endpoint for Cookidoo API discovery."""

import json
from pathlib import Path
import sys

import requests

ROOT_URL = "https://de.web.production-eu.cookidoo.vorwerk-digital.com/.well-known/home"
OUT_DIR = Path("well-known-snapshots")
TIMEOUT = 10


def fetch_json(url: str) -> dict:
    """Fetch JSON document from URL."""
    r = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": "python/requests"})
    r.raise_for_status()
    return r.json()


def normalize_links(links: dict) -> dict:
    """Sort links deterministically for diff-friendly output."""
    normalized = {}
    for rel, data in sorted(links.items()):
        if isinstance(data, list):
            normalized[rel] = sorted(
                (d["href"] for d in data),
            )
        else:
            normalized[rel] = data.get("href")
    return normalized


def crawl(start_url: str):
    """Crawl well-known home endpoints starting from start_url."""
    visited: set[str] = set()
    result = {}

    queue = [start_url]

    while queue:
        url = queue.pop(0)
        if url in visited:
            continue

        visited.add(url)
        print(f"Fetching {url}")

        try:
            doc = fetch_json(url)
        except Exception as e:
            result[url] = {"error": str(e)}
            continue

        links = doc.get("_links", {})
        normalized = normalize_links(links)

        result[url] = {
            "links": normalized,
        }

        for link in links.values():
            if isinstance(link, dict):
                href = link.get("href")
                if href and href.endswith("/.well-known/home"):
                    queue.append(href)

    return result


def write_snapshot(data: dict):
    """Write snapshot to disk, return True if changed."""
    OUT_DIR.mkdir(exist_ok=True)
    latest = OUT_DIR / "latest.json"

    serialized = json.dumps(data, indent=2, sort_keys=True)

    if latest.exists():
        if latest.read_text(encoding="utf-8") == serialized:
            print("No changes detected.")
            return False

    latest.write_text(serialized, encoding="utf-8")
    print("Snapshot updated.")
    return True


def main():
    """Crawl the well-known home endpoint and write snapshot."""
    snapshot = crawl(ROOT_URL)
    changed = write_snapshot(snapshot)
    sys.exit(1 if changed else 0)


if __name__ == "__main__":
    main()
