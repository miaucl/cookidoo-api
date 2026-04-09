"""FastMCP server bootstrap for Cookidoo."""

from __future__ import annotations

from fastmcp import FastMCP
from fastmcp.server.lifespan import lifespan

from .config import CookidooMCPConfig
from .session import CookidooSessionManager
from .tools import register_tools


def create_server(
    config: CookidooMCPConfig | None = None,
    session_manager: CookidooSessionManager | None = None,
) -> FastMCP:
    """Create the configured FastMCP server instance."""
    resolved_config = config or CookidooMCPConfig.from_env()
    resolved_session_manager = session_manager or CookidooSessionManager(resolved_config)

    @lifespan
    async def cookidoo_lifespan(_: FastMCP):
        try:
            yield {
                "config": resolved_config,
                "session_manager": resolved_session_manager,
            }
        finally:
            await resolved_session_manager.close()

    mcp = FastMCP(
        name="Cookidoo MCP Server",
        instructions=(
            "Use these tools to inspect and plan with Cookidoo account data. "
            "Start with cookidoo_list_localizations if localization is unknown."
        ),
        lifespan=cookidoo_lifespan,
    )
    register_tools(mcp, resolved_session_manager)
    return mcp


def run() -> None:
    """Run the local stdio MCP server."""
    create_server().run()
