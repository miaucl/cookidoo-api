"""Constants for Cookidoo API."""

from typing import Final

DEFAULT_API_HEADERS: Final = {
    "ACCEPT": "application/json",
}

CIAM_LOGIN_SRV_URL: Final = (
    "https://ciam.prod.cookidoo.vorwerk-digital.com/login-srv/login"
)
LOGIN_PATH: Final = "profile/{language}/login"
LOGIN_REDIRECT: Final = "%2Ffoundation%2F{language}%2Ffor-you"
RECIPE_PATH: Final = "recipes/recipe/{language}/{id}"
CUSTOM_RECIPES_PATH: Final = "created-recipes/{language}"
CUSTOM_RECIPES_PATH_ACCEPT: Final = (
    "application/vnd.vorwerk.customer-recipe.full+json"
)
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
