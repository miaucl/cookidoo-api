"""Command-line entrypoint for the Cookidoo MCP server."""

from __future__ import annotations

import asyncio
import sys

from .server import run


def main() -> None:
    """Start the local stdio Cookidoo MCP server."""
    if sys.platform == "win32" and hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    run()


if __name__ == "__main__":
    main()
