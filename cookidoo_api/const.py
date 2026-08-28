"""Constants for Cookidoo API."""

from typing import Final

DEFAULT_API_HEADERS: Final = {
    "ACCEPT": "application/json",
}

# A browser-like User-Agent for the login flow requests only. The login
# flow is served behind Cloudflare and clients without a recognizable
# browser User-Agent (e.g. Home Assistant's default "Home Assistant/x.y
# aiohttp/x.y Python/x.y") are more likely to be flagged as bots, causing
# intermittent 403s. This does not touch the caller's session defaults,
# it is only sent with the login requests below.
# See https://github.com/miaucl/cookidoo-api/issues/230
LOGIN_HEADERS: Final = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
}

CIAM_BASE_URL: Final = "https://ciam.prod.cookidoo.vorwerk-digital.com"
CIAM_LOGIN_SRV_URL: Final = f"{CIAM_BASE_URL}/login-srv/login"
OIDC_DISCOVERY_URL: Final = f"{CIAM_BASE_URL}/.well-known/openid-configuration"

# OAuth2 / OIDC client. The bearer token it yields works against the same
# api_endpoint as the previous cookie session, and additionally reaches the
# remote-monitoring backend (which the cookie session could not).
#
# The client credentials (id, secret, redirect uri) are NOT shipped with this
# library and must be supplied by the caller via `CookidooConfig`; see
# `docs/oauth-client.md` for how to obtain them.
OAUTH_SCOPE: Final = "openid profile email offline offline_access"
# Refresh a little before the (12h) access token actually expires.
TOKEN_EXPIRY_MARGIN_S: Final = 300

LOGIN_PATH: Final = "profile/{language}/login"
LOGIN_REDIRECT: Final = "%2Ffoundation%2F{language}%2Ffor-you"
RECIPE_PATH: Final = "recipes/recipe/{language}/{id}"
CUSTOM_RECIPES_PATH: Final = "created-recipes/{language}"
CUSTOM_RECIPES_PATH_ACCEPT: Final = "application/vnd.vorwerk.customer-recipe.full+json"
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
SUBSCRIPTIONS_PATH: Final = "ownership/subscriptions"

# Paired Thermomix appliances on the account. Returns the machine types, e.g.
# ``["TM7"]``. Language-independent path (customer-devices service).
DEVICES_PATH: Final = "customer-devices/api/my-devices/versions"

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
