# Purpose

Defines the Cookidoo MCP tools for localization discovery, account and recipe access, shopping lists, custom collections, and calendar planning.

## Requirements

### Requirement: Localization discovery tool
The system SHALL expose a read-only `cookidoo_list_localizations` tool that returns valid Cookidoo localization options and supports filtering by country code and language.

#### Scenario: Filter localization options by country
- **WHEN** the caller invokes `cookidoo_list_localizations` with a country filter
- **THEN** the server returns only localization entries that match that country
- **AND** each entry includes the country code, language, and localization URL needed for configuration

### Requirement: Account and recipe lookup tools
The system SHALL expose read-only `cookidoo_get_account_summary` and `cookidoo_get_recipe_details` tools. `cookidoo_get_account_summary` MUST return both user profile data and subscription state. `cookidoo_get_recipe_details` MUST return structured recipe metadata for a provided recipe ID.

#### Scenario: Fetch account summary after authentication
- **WHEN** the caller invokes `cookidoo_get_account_summary`
- **THEN** the server authenticates if needed
- **AND** returns user profile information together with the active subscription state or lack of subscription

#### Scenario: Fetch recipe details by recipe ID
- **WHEN** the caller invokes `cookidoo_get_recipe_details` with a recipe ID
- **THEN** the server returns recipe details for that ID
- **AND** the result includes structured fields that support follow-up planning actions

### Requirement: Shopping list tools
The system SHALL expose `cookidoo_get_shopping_list`, `cookidoo_add_recipe_ingredients_to_shopping_list`, `cookidoo_remove_recipe_ingredients_from_shopping_list`, and `cookidoo_clear_shopping_list` tools for recipe-based shopping list planning.

#### Scenario: View current shopping list state
- **WHEN** the caller invokes `cookidoo_get_shopping_list`
- **THEN** the server returns the current shopping list state
- **AND** the result includes both recipe-linked shopping entries and additional list items when available

#### Scenario: Add recipe ingredients to the shopping list
- **WHEN** the caller invokes `cookidoo_add_recipe_ingredients_to_shopping_list` with one or more recipe IDs
- **THEN** the server adds the ingredients for those recipes to the shopping list
- **AND** returns the added items in structured form

#### Scenario: Remove recipe ingredients from the shopping list
- **WHEN** the caller invokes `cookidoo_remove_recipe_ingredients_from_shopping_list` with one or more recipe IDs
- **THEN** the server removes the corresponding recipe ingredients from the shopping list
- **AND** returns a confirmation describing what was removed

#### Scenario: Clear the shopping list
- **WHEN** the caller invokes `cookidoo_clear_shopping_list`
- **THEN** the server removes all current shopping list entries
- **AND** returns a confirmation that the list is empty

### Requirement: Custom collection tools
The system SHALL expose `cookidoo_list_custom_collections`, `cookidoo_create_custom_collection`, `cookidoo_add_recipes_to_custom_collection`, and `cookidoo_remove_recipe_from_custom_collection` tools for managing custom Cookidoo collections.

#### Scenario: List existing custom collections
- **WHEN** the caller invokes `cookidoo_list_custom_collections`
- **THEN** the server returns the caller's custom collections
- **AND** each collection includes identifiers and names suitable for follow-up mutation calls

#### Scenario: Create a new custom collection
- **WHEN** the caller invokes `cookidoo_create_custom_collection` with a collection name
- **THEN** the server creates the collection
- **AND** returns the created collection identifier and metadata

#### Scenario: Add recipes to a custom collection
- **WHEN** the caller invokes `cookidoo_add_recipes_to_custom_collection` with a custom collection ID and one or more recipe IDs
- **THEN** the server adds the recipes to that collection
- **AND** returns the updated collection membership or a confirmation that includes the affected IDs

#### Scenario: Remove a recipe from a custom collection
- **WHEN** the caller invokes `cookidoo_remove_recipe_from_custom_collection` with a custom collection ID and recipe ID
- **THEN** the server removes that recipe from the collection
- **AND** returns a confirmation that identifies the removed recipe and collection

### Requirement: Calendar planning tools
The system SHALL expose `cookidoo_get_calendar_week`, `cookidoo_add_recipes_to_calendar`, and `cookidoo_remove_recipe_from_calendar` tools for planning recipes into a Cookidoo calendar week.

#### Scenario: Retrieve a calendar week
- **WHEN** the caller invokes `cookidoo_get_calendar_week` for a date
- **THEN** the server returns the calendar entries for that week
- **AND** each day result includes the recipes scheduled for that day

#### Scenario: Add recipes to the calendar
- **WHEN** the caller invokes `cookidoo_add_recipes_to_calendar` with a date and one or more recipe IDs
- **THEN** the server schedules those recipes on the requested day
- **AND** returns a confirmation or structured result that identifies the scheduled recipes

#### Scenario: Remove a recipe from the calendar
- **WHEN** the caller invokes `cookidoo_remove_recipe_from_calendar` with a date and recipe ID
- **THEN** the server removes that recipe from the requested day
- **AND** returns a confirmation that identifies the removed recipe and date

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
