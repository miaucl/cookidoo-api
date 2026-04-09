## 1. Constants and Types

- [x] 1.1 Add Algolia and search token constants to `cookidoo_api/const.py` (application ID, Algolia endpoint, index name patterns, search token path, default asset host, default image transformation)
- [x] 1.2 Add `CookidooSearchSort` enum to `cookidoo_api/types.py` with members: RELEVANCE, NEWEST, NAME_ASC, RATING, TOTAL_TIME, PREP_TIME
- [x] 1.3 Add `CookidooSearchFilters` dataclass to `cookidoo_api/types.py` with optional fields: category, difficulty, max_total_time, max_prep_time, tm_version, accessories, portions, min_rating
- [x] 1.4 Add `CookidooSearchRecipeHit` dataclass to `cookidoo_api/types.py` with fields: id, title, rating, number_of_ratings, total_time, image
- [x] 1.5 Add `CookidooSearchResult` dataclass to `cookidoo_api/types.py` with fields: total_hits, page, total_pages, hits (list of CookidooSearchRecipeHit)
- [x] 1.6 Add raw JSON TypedDicts for search responses to `cookidoo_api/raw_types.py`

## 2. Helpers

- [x] 2.1 Add `cookidoo_search_recipe_hit_from_json` helper to `cookidoo_api/helpers.py` that parses an Algolia hit dict into `CookidooSearchRecipeHit`, resolving image URL template placeholders
- [x] 2.2 Add `build_algolia_filter_string` helper to `cookidoo_api/helpers.py` that converts a `CookidooSearchFilters` instance into an Algolia filter string

## 3. Core Client

- [x] 3.1 Add private `_get_search_token` method to `Cookidoo` class that fetches and caches the Algolia API key from the Cookidoo search token endpoint
- [x] 3.2 Add private `_get_search_domain` method to derive the Cookidoo web domain from localization config for the token endpoint URL
- [x] 3.3 Add private `_get_market_code` method to derive the Algolia market code from localization config
- [x] 3.4 Add `search_recipes` public method to `Cookidoo` class accepting query, page, page_size, sort, and filters; returns `CookidooSearchResult`

## 4. MCP Tool

- [x] 4.1 Add `cookidoo_search_recipes` tool handler in `cookidoo_api/mcp/tools.py` with parameters: query, page, page_size, sort, category, difficulty, max_total_time_minutes, max_prep_time_minutes, tm_version, accessories, portions, min_rating
- [x] 4.2 Register the tool with `API_READONLY_ANNOTATIONS` and a descriptive docstring

## 5. Tests

- [x] 5.1 Add mock Algolia search response fixtures to `tests/responses.py`
- [x] 5.2 Add unit tests for `search_recipes` in `tests/test_cookidoo.py` covering: keyword search, pagination, sort orders, filters, empty query, token refresh
- [x] 5.3 Add unit tests for `build_algolia_filter_string` in `tests/test_helpers.py`
- [x] 5.4 Add unit tests for `cookidoo_search_recipe_hit_from_json` in `tests/test_helpers.py`
- [x] 5.5 Add MCP tool tests for `cookidoo_search_recipes` in `tests/test_mcp.py`

## 6. Exports and Documentation

- [x] 6.1 Export new types and enum from `cookidoo_api/__init__.py`
- [x] 6.2 Update `example.py` with a search usage example
