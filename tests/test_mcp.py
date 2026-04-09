"""Tests for the Cookidoo MCP server."""

from datetime import date
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock

from aiohttp import ClientSession
from fastmcp.exceptions import ToolError
import pytest

from cookidoo_api.cookidoo import Cookidoo
from cookidoo_api.exceptions import CookidooAuthException, CookidooParseException
from cookidoo_api.mcp.config import CookidooMCPConfig, CookidooMCPConfigError
from cookidoo_api.mcp.errors import to_tool_error
from cookidoo_api.mcp.serialization import make_tool_result
from cookidoo_api.mcp.server import create_server
from cookidoo_api.mcp.session import CookidooSessionManager
from cookidoo_api.mcp.tools import (
    handle_add_recipes_to_calendar,
    handle_get_account_summary,
    handle_get_shopping_list,
    handle_list_custom_collections,
    handle_search_recipes,
)
from cookidoo_api.types import (
    CookidooAdditionalItem,
    CookidooCalendarDay,
    CookidooCollection,
    CookidooConfig,
    CookidooIngredientItem,
    CookidooLocalizationConfig,
    CookidooSearchRecipeHit,
    CookidooSearchResult,
    CookidooShoppingRecipe,
    CookidooSubscription,
    CookidooUserInfo,
)


class DummySession:
    """Minimal aiohttp-like session for session-manager tests."""

    def __init__(self) -> None:
        """Initialize the dummy session."""
        self.closed = False

    async def close(self) -> None:
        """Mark the session as closed."""
        self.closed = True


class FakeCookidooClient:
    """Minimal Cookidoo client double used by the session manager."""

    def __init__(self, session: DummySession, cfg: CookidooConfig) -> None:
        """Store constructor arguments for assertions."""
        self.session = session
        self.cfg = cfg
        self.auth_data: object | None = None
        self.expires_in = 3600
        self.login_calls = 0
        self.refresh_calls = 0

    async def login(self) -> None:
        """Simulate a successful login."""
        self.login_calls += 1
        self.auth_data = object()

    async def refresh_token(self) -> None:
        """Simulate a token refresh."""
        self.refresh_calls += 1
        self.auth_data = object()


class FakeToolSessionManager:
    """Simple session-manager double for tool-handler tests."""

    def __init__(self, client: object) -> None:
        """Return the provided client from get_client."""
        self.get_client = AsyncMock(return_value=cast(Cookidoo, client))


def _sample_recipe(recipe_id: str = "r1", name: str = "Recipe") -> CookidooShoppingRecipe:
    """Build a minimal shopping-recipe object."""
    return CookidooShoppingRecipe(
        id=recipe_id,
        name=name,
        ingredients=[],
        thumbnail=None,
        image=None,
        url=f"https://example.invalid/{recipe_id}",
    )


def _sample_collection(
    collection_id: str = "col1",
    name: str = "Collection",
) -> CookidooCollection:
    """Build a minimal collection object."""
    return CookidooCollection(
        id=collection_id,
        name=name,
        description=None,
        chapters=[],
    )


def _sample_calendar_day(day_id: str = "2026-04-09") -> CookidooCalendarDay:
    """Build a minimal calendar-day object."""
    return CookidooCalendarDay(
        id=day_id,
        title=day_id,
        recipes=[],
    )


class TestCookidooMCPConfig:
    """Tests for MCP environment configuration."""

    def test_require_credentials_reports_missing_values(self) -> None:
        """Authenticated tools should fail clearly when credentials are absent."""
        config = CookidooMCPConfig()

        with pytest.raises(CookidooMCPConfigError, match="COOKIDOO_EMAIL"):
            config.require_credentials()

    async def test_resolve_localization_rejects_ambiguous_partial_filter(self) -> None:
        """A partial filter that matches multiple options should be rejected."""
        config = CookidooMCPConfig(country_code="ch")

        with pytest.raises(CookidooMCPConfigError, match="matched 4 options"):
            await config.resolve_localization()

    async def test_resolve_localization_accepts_exact_pair(self) -> None:
        """A full country/language pair should resolve to one localization."""
        config = CookidooMCPConfig(country_code="ie", language="en-GB")

        localization = await config.resolve_localization()

        assert localization.country_code == "ie"
        assert localization.language == "en-GB"
        assert localization.url.endswith("/foundation/en-GB")


class TestCookidooSessionManager:
    """Tests for lazy session and authentication handling."""

    async def test_session_manager_logs_in_refreshes_and_closes(self) -> None:
        """The manager should lazily log in, refresh, and close the session."""
        dummy_session = DummySession()
        created_clients: list[FakeCookidooClient] = []

        def session_factory() -> ClientSession:
            return cast(ClientSession, dummy_session)

        def client_factory(session: ClientSession, cfg: CookidooConfig) -> Cookidoo:
            client = FakeCookidooClient(cast(DummySession, session), cfg)
            created_clients.append(client)
            return cast(Cookidoo, client)

        manager = CookidooSessionManager(
            config=CookidooMCPConfig(
                email="user@example.invalid",
                password="secret",
            ),
            session_factory=session_factory,
            client_factory=client_factory,
        )

        first_client = await manager.get_client()
        second_client = await manager.get_client()

        fake_client = created_clients[0]
        assert first_client is second_client
        assert fake_client.login_calls == 1
        assert fake_client.cfg.localization == CookidooLocalizationConfig()

        fake_client.expires_in = 0
        await manager.get_client()
        assert fake_client.refresh_calls == 1

        await manager.close()
        assert dummy_session.closed is True


class TestCookidooMCPHelpers:
    """Tests for shared result and error helpers."""

    def test_make_tool_result_serializes_dataclasses_and_dates(self) -> None:
        """Structured content should be JSON-compatible."""
        result = make_tool_result(
            summary="Loaded account summary.",
            payload={
                "user_info": CookidooUserInfo(
                    username="Test User",
                    description=None,
                    picture=None,
                ),
                "day": date(2026, 4, 9),
            },
        )

        assert result.structured_content == {
            "user_info": {
                "username": "Test User",
                "description": None,
                "picture": None,
            },
            "day": "2026-04-09",
        }

    def test_to_tool_error_maps_known_exceptions(self) -> None:
        """Known library failures should become recoverable tool errors."""
        auth_error = to_tool_error(CookidooAuthException("Bad credentials."))
        parse_error = to_tool_error(CookidooParseException("Unexpected response."))

        assert isinstance(auth_error, ToolError)
        assert "Verify your Cookidoo credentials and localization" in str(auth_error)
        assert "response format may have changed" in str(parse_error)


class TestCookidooMCPServer:
    """Tests for FastMCP server registration."""

    async def test_create_server_registers_expected_tools(self) -> None:
        """The server should expose the initial curated tool set."""
        server = create_server(config=CookidooMCPConfig())

        tools = await server.list_tools()
        tool_names = {tool.name for tool in tools}

        assert {
            "cookidoo_list_localizations",
            "cookidoo_get_account_summary",
            "cookidoo_get_recipe_details",
            "cookidoo_get_shopping_list",
            "cookidoo_list_custom_collections",
            "cookidoo_get_calendar_week",
            "cookidoo_add_recipe_ingredients_to_shopping_list",
            "cookidoo_remove_recipe_ingredients_from_shopping_list",
            "cookidoo_clear_shopping_list",
            "cookidoo_create_custom_collection",
            "cookidoo_add_recipes_to_custom_collection",
            "cookidoo_remove_recipe_from_custom_collection",
            "cookidoo_add_recipes_to_calendar",
            "cookidoo_remove_recipe_from_calendar",
        }.issubset(tool_names)


class TestCookidooMCPToolHandlers:
    """Tests for representative MCP tool handlers."""

    async def test_handle_get_account_summary_returns_structured_content(self) -> None:
        """Account summary should combine profile and subscription data."""
        client = SimpleNamespace(
            get_user_info=AsyncMock(
                return_value=CookidooUserInfo(
                    username="Test User",
                    description="Cookidoo fan",
                    picture=None,
                )
            ),
            get_active_subscription=AsyncMock(
                return_value=CookidooSubscription(
                    active=True,
                    expires="2026-05-01T00:00:00Z",
                    start_date="2026-04-01T00:00:00Z",
                    status="RUNNING",
                    subscription_level="PREMIUM",
                    subscription_source="COMMERCE",
                    type="TRIAL",
                    extended_type="TRIAL",
                )
            ),
        )
        session_manager = cast(
            CookidooSessionManager,
            FakeToolSessionManager(client),
        )

        result = await handle_get_account_summary(session_manager)

        assert result.structured_content["user_info"]["username"] == "Test User"
        assert result.structured_content["subscription"]["active"] is True

    async def test_handle_get_shopping_list_returns_all_sections(self) -> None:
        """Shopping-list payloads should include additional items as well."""
        client = SimpleNamespace(
            get_shopping_list_recipes=AsyncMock(
                return_value=[_sample_recipe(recipe_id="r1", name="Bread")]
            ),
            get_ingredient_items=AsyncMock(
                return_value=[
                    CookidooIngredientItem(
                        id="ing1",
                        name="Flour",
                        is_owned=False,
                        description="500 g",
                    )
                ]
            ),
            get_additional_items=AsyncMock(
                return_value=[
                    CookidooAdditionalItem(
                        id="extra1",
                        name="Milk",
                        is_owned=False,
                    )
                ]
            ),
        )
        session_manager = cast(
            CookidooSessionManager,
            FakeToolSessionManager(client),
        )

        result = await handle_get_shopping_list(session_manager)

        assert result.structured_content["recipes"][0]["name"] == "Bread"
        assert result.structured_content["ingredient_items"][0]["description"] == "500 g"
        assert result.structured_content["additional_items"][0]["name"] == "Milk"

    async def test_handle_list_custom_collections_paginates(self) -> None:
        """Custom collection listing should merge all available pages."""
        client = SimpleNamespace(
            count_custom_collections=AsyncMock(return_value=(3, 2)),
            get_custom_collections=AsyncMock(
                side_effect=[
                    [
                        _sample_collection("col1", "Breakfast"),
                        _sample_collection("col2", "Dinner"),
                    ],
                    [_sample_collection("col3", "Dessert")],
                ]
            ),
        )
        session_manager = cast(
            CookidooSessionManager,
            FakeToolSessionManager(client),
        )

        result = await handle_list_custom_collections(session_manager)

        assert result.structured_content["count"] == 3
        assert [item["id"] for item in result.structured_content["collections"]] == [
            "col1",
            "col2",
            "col3",
        ]

    async def test_handle_add_recipes_to_calendar_returns_updated_day(self) -> None:
        """Calendar mutations should return the updated day payload."""
        client = SimpleNamespace(
            add_recipes_to_calendar=AsyncMock(
                return_value=_sample_calendar_day("2026-04-09")
            )
        )
        session_manager = cast(
            CookidooSessionManager,
            FakeToolSessionManager(client),
        )

        result = await handle_add_recipes_to_calendar(
            session_manager=session_manager,
            day=date(2026, 4, 9),
            recipe_ids=["r1", "r2"],
        )

        assert result.structured_content["recipe_ids"] == ["r1", "r2"]
        assert result.structured_content["calendar_day"]["id"] == "2026-04-09"

    async def test_handle_search_recipes_returns_structured_results(self) -> None:
        """Search should return structured results with hits and pagination."""
        client = SimpleNamespace(
            search_recipes=AsyncMock(
                return_value=CookidooSearchResult(
                    total_hits=150,
                    page=0,
                    total_pages=8,
                    hits=[
                        CookidooSearchRecipeHit(
                            id="r130616",
                            title="Tomaten-Knoblauch-Pasta",
                            rating=4.1,
                            number_of_ratings=5258,
                            total_time=1800,
                            image="https://assets.tmecosys.com/image.jpg",
                        ),
                    ],
                )
            )
        )
        session_manager = cast(
            CookidooSessionManager,
            FakeToolSessionManager(client),
        )

        result = await handle_search_recipes(
            session_manager=session_manager,
            query="Pasta",
            page=0,
            page_size=20,
            sort=None,
            category=None,
            difficulty=None,
            max_total_time_minutes=None,
            max_prep_time_minutes=None,
            tm_version=None,
            accessories=None,
            portions=None,
            min_rating=None,
        )

        assert result.structured_content["total_hits"] == 150
        assert result.structured_content["page"] == 0
        assert result.structured_content["total_pages"] == 8
        assert len(result.structured_content["hits"]) == 1
        assert result.structured_content["hits"][0]["id"] == "r130616"
