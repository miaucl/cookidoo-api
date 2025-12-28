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


def extract_root_links(snapshot: dict) -> dict:
    """Extract rel -> href mapping from root .well-known/home."""
    root = next(iter(snapshot.values()))
    return root.get("links", {})


def diff_links(old: dict, new: dict) -> dict:
    """Diff two rel -> href mappings."""
    old_keys = set(old.keys())
    new_keys = set(new.keys())

    added = sorted(new_keys - old_keys)
    removed = sorted(old_keys - new_keys)

    changed = sorted(k for k in old_keys & new_keys if old[k] != new[k])

    return {
        "added": added,
        "removed": removed,
        "changed": changed,
    }


def mermaid_graph(snapshot: dict) -> str:
    """Generate mermaid graph from snapshot."""
    root_url = next(iter(snapshot.keys()))
    root_links = snapshot[root_url]["links"]

    lines = ["graph TD"]
    lines.append("  root[.well-known/home]")

    for rel in sorted(root_links.keys()):
        node = rel.replace(":", "_")
        lines.append(f"  root --> {node}[{rel}]")

    return "\n".join(lines)


def main():
    """Crawl and snapshot well-known discovery."""
    snapshot = crawl(ROOT_URL)

    latest_path = OUT_DIR / "latest.json"
    old_snapshot = None
    if latest_path.exists():
        old_snapshot = json.loads(latest_path.read_text())

    changed = write_snapshot(snapshot)

    if old_snapshot:
        old_links = extract_root_links(old_snapshot)
        new_links = extract_root_links(snapshot)
        diff = diff_links(old_links, new_links)

        Path("diff-summary.json").write_text(
            json.dumps(diff, indent=2), encoding="utf-8"
        )

        Path("api-graph.mmd").write_text(mermaid_graph(snapshot), encoding="utf-8")

    sys.exit(1 if changed else 0)


if __name__ == "__main__":
    main()
