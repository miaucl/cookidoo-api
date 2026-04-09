## ADDED Requirements

### Requirement: Recipe search tool
The system SHALL expose a read-only `cookidoo_search_recipes` tool that searches Cookidoo recipes by keyword with optional filters for category, difficulty, time limits, Thermomix version, accessories, portions, ratings, sort order, and pagination.

#### Scenario: Search recipes by keyword
- **WHEN** the caller invokes `cookidoo_search_recipes` with a query string
- **THEN** the server returns structured search results including total hit count, page metadata, and a list of recipe hits with IDs, titles, ratings, times, and image URLs

#### Scenario: Search with filters
- **WHEN** the caller invokes `cookidoo_search_recipes` with filter parameters such as category, difficulty, or max time
- **THEN** the server applies those filters to narrow the search results
- **AND** returns only matching recipes

#### Scenario: Paginate search results
- **WHEN** the caller invokes `cookidoo_search_recipes` with page and page_size parameters
- **THEN** the server returns the requested page of results
- **AND** the result metadata includes total hits and total pages for the caller to request further pages

#### Scenario: Sort search results
- **WHEN** the caller invokes `cookidoo_search_recipes` with a sort parameter
- **THEN** the server returns results ordered according to the specified sort order
