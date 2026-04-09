## Context

The Cookidoo API client (`Cookidoo` class) currently uses the mobile API at `{country_code}.tmmobile.vorwerk-digital.com` for all operations. Recipe search on Cookidoo is powered by a separate backend: **Algolia** (application ID `3TA8NT85XJ`). The web frontend obtains a time-limited Algolia API key from a Cookidoo token endpoint, then queries Algolia directly.

The MCP server already wraps 14 tools via FastMCP and manages a single authenticated session per process. Search needs to integrate alongside this existing infrastructure.

## Goals / Non-Goals

**Goals:**
- Add a `search_recipes` method to the `Cookidoo` class that queries Algolia for recipes with support for keyword search, faceted filters (category, difficulty, time, TM version, accessories, portions, ratings), sort order, and pagination.
- Manage the Algolia search token lifecycle (fetch, cache, refresh on expiry) within the existing client.
- Expose a `cookidoo_search_recipes` MCP tool with the same capabilities.
- Return structured, typed results (`CookidooSearchResult` / `CookidooSearchRecipeHit`) consistent with existing dataclass patterns.

**Non-Goals:**
- Collection search, editorial/article search, or autocomplete/suggestion endpoints -- recipe search only.
- Bypassing the Algolia token endpoint (we use the official key exchange, not hardcoded keys).
- Supporting unauthenticated / guest search -- the token endpoint requires an authenticated session.
- Ingredient-based filtering (the "include/exclude ingredients" Algolia facets use text search within Algolia, not a structured ingredient ID filter -- this is complex and deferred).

## Decisions

### 1. Search token management: integrated into `Cookidoo` class

**Decision:** Add search token fetching and caching as private methods on the `Cookidoo` class, alongside the existing OAuth2 token management.

**Rationale:** The search token endpoint (`https://cookidoo.{tld}/search/api/subscription/token`) requires the user's OAuth2 access token as a cookie (`v-token`). Keeping token management in the client avoids leaking auth details across module boundaries. The token's `validUntil` field is cached and checked before each search call, similar to how `expires_in` works for the OAuth2 token.

**Alternative considered:** Separate `AlgoliaSearchClient` class -- rejected because it would need access to the OAuth2 token and session, creating coupling without encapsulation benefit.

### 2. Algolia query: direct HTTP POST via aiohttp

**Decision:** Query Algolia's `/1/indexes/*/queries` endpoint directly using the existing `aiohttp.ClientSession`, without adding an Algolia SDK dependency.

**Rationale:** The Algolia query is a single POST endpoint with a JSON body. The request is straightforward (index name, query string, params string with filters/pagination). Adding the `algoliasearch` Python SDK would introduce a dependency for one HTTP call. The existing aiohttp session is already available.

### 3. Market code derivation from localization

**Decision:** Derive the Algolia market code (used in index names like `recipes-production-de`) from the configured `CookidooLocalizationConfig.country_code`. For `gb` (UK), use `gb`; for `xp` (international), use `en`.

**Rationale:** Algolia indices are per-market (e.g., `recipes-production-de`, `recipes-production-ch`). The market code matches the Cookidoo domain TLD, which corresponds to the `country_code` in localization config. The search token endpoint URL also uses this TLD: `https://cookidoo.{tld}/search/api/subscription/token`.

### 4. Search domain derivation

**Decision:** Derive the Cookidoo web domain for the search token endpoint from `CookidooLocalizationConfig.url` (e.g., `https://cookidoo.ch/foundation/de-CH` -> `cookidoo.ch`). This avoids hardcoding a separate domain mapping.

**Rationale:** The `url` field in localization config already contains the correct Cookidoo domain for each market. Extracting the hostname gives us the correct domain for the search token endpoint.

### 5. Filter parameters: typed dataclass with Algolia filter string builder

**Decision:** Define a `CookidooSearchFilters` dataclass with optional typed fields (category, difficulty, max_total_time, max_prep_time, tm_version, accessories, portions, min_rating). A private helper method builds the Algolia filter string from non-None fields.

**Rationale:** Typed fields provide IDE support and validation. The filter string format is Algolia-specific (`categories.id:X AND difficulty:"Y" AND totalTime <= Z`) and should be an internal detail. The filter builder is testable in isolation.

### 6. Sort order: enum mapping to index names

**Decision:** Define a `CookidooSearchSort` enum with members like `RELEVANCE`, `NEWEST`, `NAME_ASC`, `RATING`, `TOTAL_TIME`, `PREP_TIME`. Each maps to the corresponding Algolia index name suffix.

**Rationale:** Sort order in Algolia is controlled by choosing different replica indices, not by a query parameter. The enum cleanly maps user intent to the correct index name.

### 7. Image URL resolution

**Decision:** Resolve Algolia image URL templates (`{assethost}`, `{transformation}`) to concrete URLs in the helper/parser layer, using `assets.tmecosys.com` as the asset host and a reasonable default transformation preset.

**Rationale:** Raw Algolia results contain template placeholders. Returning unresolved templates would be unusable. The existing codebase already resolves image URLs in helpers for other recipe types.

### 8. MCP tool design: single tool with optional parameters

**Decision:** Expose one `cookidoo_search_recipes` tool with `query` (required), and optional `page`, `page_size`, `sort`, `category`, `difficulty`, `max_total_time_minutes`, `max_prep_time_minutes`, `tm_version`, `accessories`, `portions`, and `min_rating` parameters.

**Rationale:** A single tool with optional filters is simpler for LLM callers than separate filter/search tools. Time parameters use minutes (not seconds) in the MCP interface for user-friendliness, converted internally.

## Risks / Trade-offs

- **Algolia token endpoint stability**: The `/search/api/subscription/token` endpoint is undocumented and could change. → Mitigation: The token fetch is isolated in one method; a change only requires updating that method.
- **Index name format changes**: Algolia index names like `recipes-production-{market}` could be renamed. → Mitigation: Index name patterns are constants, easy to update.
- **Rate limiting**: Algolia may rate-limit the API key. → Mitigation: The key itself embeds rate limits; we rely on Algolia's standard behavior. No client-side rate limiting for now.
- **Token expiry race**: The search token could expire between the check and the request. → Mitigation: If a search returns 403, retry once after refreshing the token.
- **Market code edge cases**: Some localizations (e.g., `xp` for international) may not have a matching Algolia index. → Mitigation: Map known edge cases explicitly; fail with a clear error for unmapped markets.
