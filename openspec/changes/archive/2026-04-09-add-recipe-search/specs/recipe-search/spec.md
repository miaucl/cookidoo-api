## ADDED Requirements

### Requirement: Search token acquisition
The system SHALL fetch a time-limited Algolia search API key from the Cookidoo web frontend token endpoint using the authenticated session's OAuth2 access token.

#### Scenario: Fetch search token on first search call
- **WHEN** the client executes a recipe search and no valid search token is cached
- **THEN** the client requests a token from the Cookidoo search token endpoint
- **AND** caches the returned API key together with its expiration timestamp

#### Scenario: Reuse cached search token
- **WHEN** the client executes a recipe search and a cached search token has not yet expired
- **THEN** the client reuses the cached token without making a new token request

#### Scenario: Refresh expired search token
- **WHEN** the client executes a recipe search and the cached search token has expired
- **THEN** the client fetches a new token before executing the search query

### Requirement: Keyword recipe search
The system SHALL support searching Cookidoo recipes by keyword query via the Algolia search backend, returning structured, paginated results.

#### Scenario: Search recipes by keyword
- **WHEN** the caller invokes `search_recipes` with a query string
- **THEN** the client queries the Algolia recipe index for the configured market
- **AND** returns a result containing the total hit count, current page, total pages, and a list of recipe hits

#### Scenario: Empty query returns browsable results
- **WHEN** the caller invokes `search_recipes` with an empty query string
- **THEN** the client queries the empty-search-score index for the configured market
- **AND** returns popular or editorially ranked recipes

### Requirement: Search result structure
Each recipe hit returned by search SHALL include the recipe ID, title, rating, number of ratings, total time in seconds, and a resolved image URL.

#### Scenario: Recipe hit contains expected fields
- **WHEN** a search returns recipe hits
- **THEN** each hit includes `id`, `title`, `rating`, `number_of_ratings`, `total_time`, and `image`
- **AND** the `image` field contains a resolved URL (not a template with placeholders)

### Requirement: Search pagination
The system SHALL support page-based pagination for search results.

#### Scenario: Paginate through search results
- **WHEN** the caller invokes `search_recipes` with a `page` parameter
- **THEN** the client returns the corresponding page of results
- **AND** the result metadata includes the current page number and total number of pages

#### Scenario: Configurable page size
- **WHEN** the caller invokes `search_recipes` with a `page_size` parameter
- **THEN** the client requests that many hits per page from Algolia

### Requirement: Search sort order
The system SHALL support sorting search results by relevance, newest, name, rating, total time, or preparation time by querying the appropriate Algolia replica index.

#### Scenario: Sort by rating
- **WHEN** the caller invokes `search_recipes` with sort set to rating
- **THEN** the client queries the rating-descending replica index
- **AND** results are ordered by highest rating first

#### Scenario: Default sort is relevance
- **WHEN** the caller invokes `search_recipes` without specifying a sort order
- **THEN** the client uses the default relevance index

### Requirement: Search filters
The system SHALL support filtering search results by category, difficulty, maximum total time, maximum preparation time, Thermomix version, accessories, portions, and minimum rating.

#### Scenario: Filter by category
- **WHEN** the caller invokes `search_recipes` with a category filter
- **THEN** the client includes a `categories.id` filter in the Algolia query
- **AND** only recipes in that category are returned

#### Scenario: Filter by difficulty
- **WHEN** the caller invokes `search_recipes` with a difficulty filter
- **THEN** the client includes a `difficulty` filter in the Algolia query
- **AND** only recipes matching that difficulty level are returned

#### Scenario: Filter by maximum total time
- **WHEN** the caller invokes `search_recipes` with a max total time filter
- **THEN** the client includes a `totalTime <=` filter in the Algolia query
- **AND** only recipes within that time limit are returned

#### Scenario: Combine multiple filters
- **WHEN** the caller invokes `search_recipes` with multiple filter parameters
- **THEN** the client combines them with AND logic in the Algolia filter string
- **AND** only recipes matching all filters are returned

### Requirement: Market-aware index selection
The system SHALL derive the Algolia market code from the configured localization and use it to construct the correct index name for search queries.

#### Scenario: German market uses de index
- **WHEN** the client is configured with country code `de`
- **THEN** search queries target the `recipes-production-de` family of indices

#### Scenario: Unknown market produces a clear error
- **WHEN** the client is configured with a country code that has no matching Algolia index
- **THEN** the search method raises an actionable error identifying the unsupported market
