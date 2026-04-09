"""Constants for Cookidoo API."""

from typing import Final

COOKIDOO_CLIENT_ID: Final = "kupferwerk-client-nwot"
COOKIDOO_CLIENT_SECRET: Final = "Ls50ON1woySqs1dCdJge"
COOKIDOO_AUTHORIZATION_HEADER: Final = (
    "Basic a3VwZmVyd2Vyay1jbGllbnQtbndvdDpMczUwT04xd295U3FzMWRDZEpnZQ=="
)
# "$COOKIDOO_CLIENT_ID:$COOKIDOO_CLIENT_SECRET"

DEFAULT_TOKEN_HEADERS: Final = {
    "ACCEPT": "application/json",
    "CONTENT-TYPE": "application/x-www-form-urlencoded",
    "AUTHORIZATION": COOKIDOO_AUTHORIZATION_HEADER,
}
DEFAULT_API_HEADERS: Final = {
    "ACCEPT": "application/json",
}
AUTHORIZATION_HEADER: Final = "{type} {access_token}"
COOKIE_HEADER: Final = "v-token={access_token}"

INTERNATIONAL_COUNTRY_CODE: Final = "xp"
CO_UK_COUNTRY_CODE: Final = "gb"

API_ENDPOINT: Final = "https://{country_code}.tmmobile.vorwerk-digital.com"
TOKEN_PATH: Final = "ciam/auth/token"
RECIPE_PATH: Final = "recipes/recipe/{language}/{id}"
CUSTOM_RECIPE_PATH: Final = "created-recipes/{language}/{id}"
ADD_CUSTOM_RECIPE_PATH: Final = "created-recipes/{language}"
REMOVE_CUSTOM_RECIPE_PATH: Final = "created-recipes/{language}/{id}"
SHOPPING_LIST_RECIPES_PATH: Final = "shopping/{language}"
INGREDIENT_ITEMS_PATH: Final = "shopping/{language}"
EDIT_OWNERSHIP_INGREDIENT_ITEMS_PATH: Final = (
    "shopping/{language}/owned-ingredients/ownership/edit"
)
ADD_INGREDIENT_ITEMS_FOR_RECIPES_PATH: Final = "shopping/{language}/recipes/add"
REMOVE_INGREDIENT_ITEMS_FOR_RECIPES_PATH: Final = "shopping/{language}/recipes/remove"
ADDITIONAL_ITEMS_PATH: Final = "shopping/{language}"
ADD_ADDITIONAL_ITEMS_PATH: Final = "shopping/{language}/additional-items/add"
EDIT_ADDITIONAL_ITEMS_PATH: Final = "shopping/{language}/additional-items/edit"
EDIT_OWNERSHIP_ADDITIONAL_ITEMS_PATH: Final = (
    "shopping/{language}/additional-items/ownership/edit"
)
REMOVE_ADDITIONAL_ITEMS_PATH: Final = "shopping/{language}/additional-items/remove"

COMMUNITY_PROFILE_PATH: Final = "community/profile"
MOBILE_NOTIFICATIONS_PATH: Final = (
    "https://ch.tmmobile.vorwerk-digital.com/ownership/{language}/mobile-notifications"
)
SUBSCRIPTIONS_PATH: Final = "ownership/subscriptions"

CUSTOM_COLLECTIONS_PATH: Final = "organize/{language}/api/custom-list"
CUSTOM_COLLECTIONS_PATH_ACCEPT: Final = (
    "application/vnd.vorwerk.organize.custom-list.mobile+json"
)
ADD_CUSTOM_COLLECTION_PATH: Final = "organize/{language}/api/custom-list"
REMOVE_CUSTOM_COLLECTION_PATH: Final = "organize/{language}/api/custom-list/{id}"
ADD_RECIPES_TO_CUSTOM_COLLECTION_PATH: Final = (
    "organize/{language}/api/custom-list/{id}"
)
REMOVE_RECIPE_FROM_CUSTOM_COLLECTION_PATH: Final = (
    "organize/{language}/api/custom-list/{id}/recipes/{recipe}"
)
MANAGED_COLLECTIONS_PATH: Final = "organize/{language}/api/managed-list"
MANAGED_COLLECTIONS_PATH_ACCEPT: Final = (
    "application/vnd.vorwerk.organize.managed-list.mobile+json"
)
ADD_MANAGED_COLLECTION_PATH: Final = "organize/{language}/api/managed-list"
REMOVE_MANAGED_COLLECTION_PATH: Final = "organize/{language}/api/managed-list/{id}"
RECIPES_IN_CALENDAR_WEEK_PATH: Final = "planning/{language}/api/my-week/{day}"
ADD_RECIPES_TO_CALENDER_PATH: Final = "planning/{language}/api/my-day"
REMOVE_RECIPE_FROM_CALENDER_PATH: Final = (
    "planning/{language}/api/my-day/{day}/recipes/{recipe}"
)

DEFAULT_SITE = "eu"

# Algolia search constants
ALGOLIA_APPLICATION_ID: Final = "3TA8NT85XJ"
ALGOLIA_ENDPOINT: Final = (
    "https://{app_id}-dsn.algolia.net/1/indexes/*/queries"
)
ALGOLIA_INDEX_PATTERN: Final = "recipes-production-{market}"
ALGOLIA_EMPTY_SEARCH_INDEX_PATTERN: Final = (
    "recipes-production-{market}-by-emptySearchScore"
)
ALGOLIA_SORT_INDEX_SUFFIXES: Final = {
    "relevance": "",
    "newest": "-by-publishedAt-desc",
    "name_asc": "-by-title-asc",
    "rating": "-by-rating-desc",
    "total_time": "-by-totalTime-asc",
    "prep_time": "-by-preparationTime-asc",
}
SEARCH_TOKEN_PATH: Final = "search/api/subscription/token"
ALGOLIA_DEFAULT_PAGE_SIZE: Final = 20
ALGOLIA_ASSET_HOST: Final = "assets.tmecosys.com"
ALGOLIA_IMAGE_TRANSFORMATION: Final = "t_web_search_380x286"
