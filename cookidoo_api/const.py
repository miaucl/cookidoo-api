"""Constants for Cookidoo API."""

from typing import Final

from cookidoo_api.types import CookidooConfig

LOGIN_START_URL: Final = "https://cookidoo.ch"
LOGIN_START_SELECTOR: Final = "#layout--default > header > div > core-nav > nav > div.core-nav__container > ul.core-nav__links.unauthenticated-only > li:nth-child(2) > a"
LOGIN_EMAIL_SELECTOR: Final = "#email"
LOGIN_PASSWORD_SELECTOR: Final = "#password"
LOGIN_SUBMIT_SELECTOR: Final = 'button[type="submit"]'
LOGIN_CAPTCHA_SELECTOR: Final = "#amzn-captcha-verify-button"
LOGIN_ERROR_NOTIFICATION_SELECTOR: Final = ".notification__unobtrusive-error"
COOKIE_VALIDATION_URL: Final = "https://cookidoo.ch/profile/account"
COOKIE_VALIDATION_SELECTOR: Final = (
    "main > section > .profile-indent > .profile-main-headline"
)
SHOPPING_LIST_URL: Final = "https://cookidoo.ch/shopping"
SHOPPING_LIST_SELECTOR: Final = "pm-shopping-list"

SHOPPING_LIST_OPTIONS_SELECTOR: Final = "#shopping-list-options"
SHOPPING_LIST_CLEAR_ALL_OPTION_SELECTOR: Final = "#clearAllRecipes"
SHOPPING_LIST_CLEAR_ALL_MODAL_CONFIRM_SELECTOR: Final = (
    'core-modal [data-action="clear-all"] button[type="submit"]'
)

SHOPPING_LIST_ITEMS_SELECTOR: Final = "pm-ingredients-list #byCategory"
SHOPPING_LIST_CHECKED_ITEMS_SELECTOR: Final = "pm-checked-list-wrapper"

SHOPPING_LIST_ITEM_SUB_SELECTOR: Final = "li:not(.additional-items-list-item)"
SHOPPING_LIST_ITEM_LABEL_SUB_SELECTOR: Final = (
    'label span[data-type="ingredientNotation"]'
)
SHOPPING_LIST_ITEM_QUANTITY_SUB_SELECTOR: Final = 'label span[data-type="value"]'
SHOPPING_LIST_ITEM_UNIT_SUB_SELECTOR: Final = 'label span[data-type="unitNotation"]'
SHOPPING_LIST_ITEM_ID_SUB_SELECTOR: Final = "input[data-value]"
SHOPPING_LIST_ITEM_ID_ATTR: Final = "data-value"
SHOPPING_LIST_CHECKBOX_SUB_SELECTOR: Final = "core-checkbox"

SHOPPING_LIST_ADDITIONAL_ITEMS_SELECTOR: Final = "pm-additional-items-list"
SHOPPING_LIST_ADDITIONAL_CHECKED_ITEMS_SELECTOR: Final = "pm-checked-list-wrapper"
SHOPPING_LIST_ADDITIONAL_ITEM_SUB_SELECTOR: Final = "li.additional-items-list-item"
SHOPPING_LIST_ADDITIONAL_ITEM_HOVER_SUB_SELECTOR: Final = "> div"
SHOPPING_LIST_ADDITIONAL_ITEM_LABEL_SUB_SELECTOR: Final = (
    'label span[data-type="name"], label span[data-type="value"]'
)
SHOPPING_LIST_ADDITIONAL_ITEM_ID_SUB_SELECTOR: Final = "input[data-value]"
SHOPPING_LIST_ADDITIONAL_ITEM_ID_ATTR: Final = "data-value"
SHOPPING_LIST_ADDITIONAL_CHECKBOX_SUB_SELECTOR: Final = "core-checkbox"
SHOPPING_LIST_ADDITIONAL_ITEM_DELETE_SUB_SELECTOR: Final = 'span[data-type="delete"]'
SHOPPING_LIST_ADDITIONAL_ITEM_EDIT_SUB_SELECTOR: Final = 'span[data-type="edit"]'

SHOPPING_LIST_EDIT_ADDITIONAL_ITEM_SELECTOR: Final = "pm-edit-additional-item"
SHOPPING_LIST_EDIT_ADDITIONAL_ITEM_INPUT_SUB_SELECTOR: Final = 'input[type="text"]'
SHOPPING_LIST_EDIT_ADDITIONAL_ITEM_CONFIRM_SUB_SELECTOR: Final = (
    'button:not([type="button"])'
)

SHOPPING_LIST_CREATE_ADDITIONAL_ITEM_SELECTOR: Final = "pm-add-additional-item"
SHOPPING_LIST_CREATE_ADDITIONAL_ITEM_INPUT_SUB_SELECTOR: Final = "input"
SHOPPING_LIST_CREATE_ADDITIONAL_ITEM_CONFIRM_SUB_SELECTOR: Final = "button"

DOM_CHECK_ATTACHED: Final = "element => document.body.contains(element)"

DEFAULT_RETRIES = 3
DEFAULT_NETWORK_TIMEOUT = 5000
DEFAULT_TIMEOUT = 3000


DEFAULT_COOKIDOO_CONFIG = CookidooConfig(
    {
        "language_code": "de-CH",
        "browser": "firefox",
        "remote_addr": None,
        "remote_port": "9222",
        "headless": True,
        "email": "your@email",
        "password": "1234password!",
        "network_timeout": DEFAULT_NETWORK_TIMEOUT,
        "timeout": DEFAULT_TIMEOUT,
        "retries": DEFAULT_RETRIES,
        "tracing": False,
        "screenshots": False,
        "out_dir": "./out",
    }
)
