"""Constants for Cookidoo API."""

from typing import Final

from cookidoo_api.types import CookidooConfig, CookidooLocalizationConfig

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

TOKEN_ENDPOINT: Final = "https://{site}.login.vorwerk.com/oauth2/token"

API_ENDPOINT: Final = "https://{country_code}.tmmobile.vorwerk-digital.com"
RECIPE_PATH: Final = "recipes/recipe/{language}/{id}"
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

DEFAULT_SITE = "eu"

DEFAULT_COOKIDOO_CONFIG = CookidooConfig(
    {
        "localization": CookidooLocalizationConfig(
            {
                "country_code": "ch",
                "language": "de-CH",
                "url": "https://cookidoo.ch/foundation/de-CH",
            }
        ),
        "email": "your@email",
        "password": "1234password!",
    }
)
