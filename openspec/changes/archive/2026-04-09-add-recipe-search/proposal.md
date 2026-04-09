## Why

The Cookidoo API client and MCP server currently support recipe lookup by ID, shopping lists, collections, and calendar planning -- but there is no way to **discover** recipes. Users must already know a recipe ID to interact with it. Adding search capability closes this gap and makes the API useful for the most common Cookidoo workflow: finding recipes by keyword, category, or dietary preference.

## What Changes

- Add a new `search_recipes` method to the `Cookidoo` client that queries Cookidoo's Algolia-based search backend, including support for keyword queries, category/difficulty/time filters, sorting, and pagination.
- Add an Algolia API key management flow (fetching and refreshing time-limited search tokens from Cookidoo's web frontend).
- Introduce new types for search results (`CookidooSearchResult`, `CookidooSearchRecipeHit`, etc.) and search filter parameters.
- Expose a `cookidoo_search_recipes` MCP tool that wraps the search functionality with appropriate input parameters and structured output.
- Add constants for Algolia endpoints, index name patterns, and search defaults.

## Capabilities

### New Capabilities
- `recipe-search`: Recipe search via Cookidoo's Algolia backend, covering keyword queries, faceted filtering (category, difficulty, time, Thermomix version, accessories, portions, ratings), sort orders, and paginated results.

### Modified Capabilities
- `cookidoo-core-tools`: Adding the `cookidoo_search_recipes` tool to the existing tool set.

## Impact

- **Code**: New search method on `Cookidoo` class, new types in `types.py`/`raw_types.py`, new constants, new MCP tool handler in `tools.py`.
- **Dependencies**: No new dependencies -- Algolia is queried via plain HTTP POST (aiohttp already available).
- **APIs**: New search token endpoint (`/search/api/subscription/token`) and Algolia POST endpoint are external dependencies.
- **Auth**: Search tokens are separate from the existing OAuth2 mobile API tokens; the client needs to manage both token lifecycles independently.
