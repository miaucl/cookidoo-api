"""Cookidoo api implementation."""

from collections.abc import Callable, Mapping, Sequence
from datetime import date
from http import HTTPStatus
from http.cookies import SimpleCookie
import json
from json import JSONDecodeError
import logging
from pathlib import Path
import re
import time
import traceback
from typing import TypeVar, cast
from urllib.parse import urlparse

from aiohttp import ClientError, ClientSession
from yarl import URL

from cookidoo_api.const import (
    ADD_ADDITIONAL_ITEMS_PATH,
    ADD_CUSTOM_COLLECTION_PATH,
    ADD_CUSTOM_RECIPE_PATH,
    ADD_INGREDIENT_ITEMS_FOR_RECIPES_PATH,
    ADD_MANAGED_COLLECTION_PATH,
    ADD_RECIPES_TO_CALENDER_PATH,
    ADD_RECIPES_TO_CUSTOM_COLLECTION_PATH,
    ADDITIONAL_ITEMS_PATH,
    CIAM_LOGIN_SRV_URL,
    COMMUNITY_PROFILE_PATH,
    CUSTOM_COLLECTIONS_PATH,
    CUSTOM_COLLECTIONS_PATH_ACCEPT,
    CUSTOM_RECIPE_PATH,
    DEFAULT_API_HEADERS,
    EDIT_ADDITIONAL_ITEMS_PATH,
    EDIT_OWNERSHIP_ADDITIONAL_ITEMS_PATH,
    EDIT_OWNERSHIP_INGREDIENT_ITEMS_PATH,
    INGREDIENT_ITEMS_PATH,
    LOGIN_PATH,
    LOGIN_REDIRECT,
    MANAGED_COLLECTIONS_PATH,
    MANAGED_COLLECTIONS_PATH_ACCEPT,
    RECIPE_PATH,
    RECIPES_IN_CALENDAR_WEEK_PATH,
    REMOVE_ADDITIONAL_ITEMS_PATH,
    REMOVE_CUSTOM_COLLECTION_PATH,
    REMOVE_CUSTOM_RECIPE_PATH,
    REMOVE_INGREDIENT_ITEMS_FOR_RECIPES_PATH,
    REMOVE_MANAGED_COLLECTION_PATH,
    REMOVE_RECIPE_FROM_CALENDER_PATH,
    REMOVE_RECIPE_FROM_CUSTOM_COLLECTION_PATH,
    SHOPPING_LIST_RECIPES_PATH,
    SUBSCRIPTIONS_PATH,
)
from cookidoo_api.exceptions import (
    CookidooAuthException,
    CookidooConfigException,
    CookidooParseException,
    CookidooRequestException,
)
from cookidoo_api.helpers import (
    cookidoo_additional_item_from_json,
    cookidoo_calendar_day_from_json,
    cookidoo_collection_from_json,
    cookidoo_custom_recipe_from_json,
    cookidoo_ingredient_item_from_json,
    cookidoo_recipe_details_from_json,
    cookidoo_recipe_from_json,
    cookidoo_search_result_from_json,
    cookidoo_subscription_from_json,
    cookidoo_user_info_from_json,
    normalize_list_param,
    normalize_tmv_param,
)
from cookidoo_api.raw_types import (
    AdditionalItemJSON,
    CalendarDayJSON,
    CommunityProfileJSON,
    CustomCollectionJSON,
    CustomRecipeJSON,
    ItemJSON,
    ManagedCollectionJSON,
    PaginationJSON,
    RecipeDetailsJSON,
    RecipeJSON,
    SearchResultJSON,
    SubscriptionJSON,
)
from cookidoo_api.types import (
    CookidooAdditionalItem,
    CookidooCalendarDay,
    CookidooCollection,
    CookidooConfig,
    CookidooCustomRecipe,
    CookidooIngredientItem,
    CookidooLocalizationConfig,
    CookidooSearchResult,
    CookidooShoppingRecipe,
    CookidooShoppingRecipeDetails,
    CookidooSubscription,
    CookidooUserInfo,
    ThermomixMachineType,
)

_LOGGER = logging.getLogger(__name__)
_T = TypeVar("_T")


class Cookidoo:
    """Unofficial Cookidoo API interface."""

    _session: ClientSession
    _cfg: CookidooConfig
    _api_headers: dict[str, str]
    _logged_in: bool

    def __init__(
        self,
        session: ClientSession,
        cfg: CookidooConfig = CookidooConfig(),
    ) -> None:
        """Init function for Cookidoo API.

        Parameters
        ----------
        session
            The client session for aiohttp requests.
            Must use a ``CookieJar(unsafe=True)`` to support cross-domain
            cookies during the OAuth2 login flow.
        cfg
            Cookidoo config

        """
        self._session = session
        self._cfg = cfg
        self._api_headers = DEFAULT_API_HEADERS.copy()
        self._logged_in = False

    @property
    def localization(self) -> CookidooLocalizationConfig:
        """Localization."""
        return self._cfg.localization

    @property
    def api_endpoint(self) -> URL:
        """Get the api endpoint.

        Returns the cookidoo domain derived from the localization URL,
        e.g. ``https://cookidoo.ch`` or ``https://cookidoo.co.uk``.
        """
        parsed = urlparse(self._cfg.localization.url)
        return URL(f"{parsed.scheme}://{parsed.netloc}")

    async def _request_json(
        self,
        method: str,
        url: URL,
        operation: str,
        *,
        params: dict[str, str] | None = None,
        json: object | None = None,
        headers: dict[str, str] | None = None,
        accepted_statuses: tuple[HTTPStatus, ...] = (
            HTTPStatus.OK,
            HTTPStatus.NO_CONTENT,
        ),
        parse_response: bool = True,
    ) -> object | None:
        """Execute an HTTP request and parse its JSON response.

        Parameters
        ----------
        method
            HTTP method (e.g. "get", "post").
        url
            The target URL (without query params when using ``params``).
        operation
            Human-readable operation name for error messages.
        params
            Optional query parameters passed to aiohttp.
        json
            Optional JSON body for the request.
        headers
            Optional extra headers (merged with default API headers).
        accepted_statuses
            HTTP status codes considered successful. Defaults to 200 and 204.
            A 204 response always returns ``None`` (no body).
        parse_response
            Whether to parse a successful non-204 response as JSON.

        Returns
        -------
        object | None
            The parsed JSON response, or ``None`` for 204 No Content.

        Raises
        ------
        CookidooAuthException
            When the server responds with 401 Unauthorized.
        CookidooRequestException
            On connection timeout or other client errors.
        CookidooParseException
            When the response body cannot be parsed as JSON.

        """
        merged_headers = {**self._api_headers, **(headers or {})}

        try:
            async with self._session.request(
                method, url, headers=merged_headers, json=json, params=params
            ) as r:
                _LOGGER.debug(
                    "Response from %s [%s]: %s", url, r.status, await r.text()
                )

                if r.status == HTTPStatus.UNAUTHORIZED:
                    try:
                        errmsg = await r.json()
                    except (JSONDecodeError, ClientError):
                        _LOGGER.debug(
                            "Exception: Cannot parse request response:\n %s",
                            traceback.format_exc(),
                        )
                    else:
                        _LOGGER.debug(
                            "Exception: Cannot %s: %s",
                            operation,
                            errmsg.get("error_description", ""),
                        )
                    self._raise_auth_exception(operation)

                if r.status not in accepted_statuses:
                    r.raise_for_status()

                if r.status == HTTPStatus.NO_CONTENT:
                    return None
                if not parse_response:
                    return None
                try:
                    result: object = await r.json()
                except (JSONDecodeError, KeyError) as e:
                    _LOGGER.debug(
                        "Exception: Cannot parse %s response:\n%s",
                        operation,
                        traceback.format_exc(),
                    )
                    raise CookidooParseException(
                        f"{operation.capitalize()} failed during parsing of request response."
                    ) from e
                else:
                    return result

        except (
            CookidooAuthException,
            CookidooRequestException,
            CookidooParseException,
        ):
            raise
        except TimeoutError as e:
            _LOGGER.debug(
                "Exception: Cannot %s:\n%s", operation, traceback.format_exc()
            )
            raise CookidooRequestException(
                f"{operation.capitalize()} failed due to connection timeout."
            ) from e
        except ClientError as e:
            _LOGGER.debug(
                "Exception: Cannot %s:\n%s", operation, traceback.format_exc()
            )
            raise CookidooRequestException(
                f"{operation.capitalize()} failed due to request exception."
            ) from e

    @staticmethod
    def _raise_auth_exception(operation: str) -> None:
        """Raise the standard auth exception for request helpers."""
        raise CookidooAuthException(
            f"{operation.capitalize()} failed due to authorization failure, "
            "the authorization token is invalid or expired."
        )

    @staticmethod
    def _ensure_mapping(result: object | None, operation: str) -> Mapping[str, object]:
        """Return a mapping response or raise the standard parse exception."""
        if not isinstance(result, Mapping):
            raise CookidooParseException(
                f"{operation.capitalize()} failed during parsing of request response."
            )
        return result

    @staticmethod
    def _ensure_sequence(result: object | None, operation: str) -> Sequence[object]:
        """Return a sequence response or raise the standard parse exception."""
        if isinstance(result, str) or not isinstance(result, Sequence):
            raise CookidooParseException(
                f"{operation.capitalize()} failed during parsing of request response."
            )
        return result

    @staticmethod
    def _parse_result(operation: str, parser: Callable[[], _T]) -> _T:
        """Convert a validated JSON response into public types."""
        try:
            return parser()
        except (KeyError, TypeError, ValueError) as e:
            raise CookidooParseException(
                f"{operation.capitalize()} failed during parsing of request response."
            ) from e

    async def login(self) -> None:
        """Perform browser-based OAuth2 login.

        Follows the same redirect chain as the Cookidoo web app:
        1. Initiate login at ``cookidoo.{tld}/profile/{lang}/login``
        2. Follow redirects through OAuth2/PKCE to the CIAM login page
        3. POST credentials to the CIAM login service
        4. Follow callback redirects to capture session cookies

        After login, the session's cookie jar contains the authentication
        cookies and all subsequent API calls are authenticated automatically.

        Raises
        ------
        CookidooRequestException
            If the request fails.
        CookidooParseException
            If the login page cannot be parsed.
        CookidooAuthException
            If the login fails due to invalid credentials.

        """
        language = self._cfg.localization.language
        login_path = LOGIN_PATH.format(language=language)
        redirect = LOGIN_REDIRECT.format(language=language)
        login_url = URL(
            str(self.api_endpoint / login_path) + f"?redirectAfterLogin={redirect}",
            encoded=True,
        )

        try:
            # Step 1: Follow redirect chain to reach the CIAM login page
            async with self._session.get(login_url, allow_redirects=True) as resp:
                self._check_login_page_status(resp.status)
                login_html = await resp.text()

            # Step 2: Extract requestId from the login form
            request_id = self._extract_request_id(login_html)

            # Step 3: POST credentials to CIAM login service
            login_data = {
                "requestId": request_id,
                "username": self._cfg.email,
                "password": self._cfg.password,
            }
            async with self._session.post(
                CIAM_LOGIN_SRV_URL,
                data=login_data,
                allow_redirects=True,
            ) as resp:
                _LOGGER.debug(
                    "Login POST completed, final URL: %s (status: %s)",
                    resp.url,
                    resp.status,
                )

            # Step 4: Verify authentication cookies were set
            self._verify_auth_cookies()
            self._logged_in = True

        except CookidooAuthException:
            raise
        except CookidooParseException:
            raise
        except TimeoutError as e:
            _LOGGER.debug("Exception: Login failed:\n %s", traceback.format_exc())
            raise CookidooRequestException(
                "Authentication failed due to connection timeout."
            ) from e
        except ClientError as e:
            _LOGGER.debug("Exception: Login failed:\n %s", traceback.format_exc())
            raise CookidooRequestException(
                "Authentication failed due to request exception."
            ) from e

    @staticmethod
    def _check_login_page_status(status: int) -> None:
        """Check login page response status."""
        if status != HTTPStatus.OK:
            raise CookidooAuthException(
                f"Login flow failed: could not reach login page (status {status})."
            )

    @staticmethod
    def _extract_request_id(login_html: str) -> str:
        """Extract requestId from the CIAM login page HTML."""
        match = re.search(
            r'<input[^>]*name=["\']requestId["\'][^>]*value=["\']([^"\']+)["\']',
            login_html,
        ) or re.search(
            r'<input[^>]*value=["\']([0-9a-f-]{36})["\'][^>]*name=["\']requestId["\']',
            login_html,
        )
        if not match:
            raise CookidooParseException(
                "Login flow failed: could not extract requestId from login page."
            )
        return match.group(1)

    def _verify_auth_cookies(self) -> None:
        """Verify that required authentication cookies are present."""
        cookie_names = {c.key for c in self._session.cookie_jar}
        required_cookies = {"_oauth2_proxy", "v-authenticated"}
        if not required_cookies.issubset(cookie_names):
            raise CookidooAuthException(
                "Login failed: authentication cookies were not set. "
                "Please check your email and password."
            )

    def save_cookies(self, path: str | Path) -> None:
        """Save session cookies to a file for later reuse.

        Parameters
        ----------
        path
            Path to the file where cookies will be saved.

        """
        cookies: list[dict[str, str]] = []
        for cookie in self._session.cookie_jar:
            cookies.append(
                {
                    "key": cookie.key,
                    "value": cookie.value,
                    "domain": cookie["domain"],
                    "path": cookie["path"],
                }
            )
        Path(path).write_text(json.dumps(cookies), encoding="utf-8")

    def load_cookies(self, path: str | Path) -> None:
        """Load session cookies from a file to restore a previous session.

        Parameters
        ----------
        path
            Path to the file containing saved cookies.

        Raises
        ------
        CookidooConfigException
            If the cookie file cannot be read or parsed.

        """
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            raise CookidooConfigException(f"Cannot load cookies from {path}.") from e

        for entry in data:
            cookie: SimpleCookie = SimpleCookie()
            cookie[entry["key"]] = entry["value"]
            cookie[entry["key"]]["domain"] = entry.get("domain", "")
            cookie[entry["key"]]["path"] = entry.get("path", "/")
            self._session.cookie_jar.update_cookies(
                cookie, URL(f"https://{entry.get('domain', '')}")
            )

        # Check if required auth cookies are present
        cookie_names = {c.key for c in self._session.cookie_jar}
        required_cookies = {"_oauth2_proxy", "v-authenticated"}
        if required_cookies.issubset(cookie_names):
            self._logged_in = True

    async def get_user_info(
        self,
    ) -> CookidooUserInfo:
        """Get user info.

        Returns
        -------
        CookidooUserInfo
            The user info

        Raises
        ------
        CookidooAuthException
            When the access token is not valid anymore
        CookidooRequestException
            If the request fails.
        CookidooParseException
            If the parsing of the request response fails.

        """

        url = self.api_endpoint / COMMUNITY_PROFILE_PATH.format(
            **self._cfg.localization.__dict__
        )
        result = self._ensure_mapping(
            await self._request_json("get", url, "loading user info"),
            "loading user info",
        )
        return self._parse_result(
            "loading user info",
            lambda: cookidoo_user_info_from_json(cast(CommunityProfileJSON, result)),
        )

    async def get_active_subscription(
        self,
    ) -> CookidooSubscription | None:
        """Get active subscription if any.

        Returns
        -------
        CookidooSubscription
            The active subscription

        Raises
        ------
        CookidooAuthException
            When the access token is not valid anymore
        CookidooRequestException
            If the request fails.
        CookidooParseException
            If the parsing of the request response fails.

        """

        url = self.api_endpoint / SUBSCRIPTIONS_PATH.format(
            **self._cfg.localization.__dict__
        )
        subscriptions = self._ensure_sequence(
            await self._request_json("get", url, "loading active subscription"),
            "loading active subscription",
        )
        try:
            if subscription := next(
                (
                    subscription
                    for subscription in subscriptions
                    if isinstance(subscription, Mapping) and subscription["active"]
                ),
                None,
            ):
                return self._parse_result(
                    "loading active subscription",
                    lambda: cookidoo_subscription_from_json(
                        cast(SubscriptionJSON, subscription)
                    ),
                )
        except KeyError as e:
            raise CookidooParseException(
                "Loading active subscription failed during parsing of request response."
            ) from e
        return None

    async def get_recipe_details(self, id: str) -> CookidooShoppingRecipeDetails:
        """Get recipe details.

        Parameters
        ----------
        id
            The id of the recipe

        Returns
        -------
        CookidooShoppingRecipeDetails
            The recipe details

        Raises
        ------
        CookidooAuthException
            When the access token is not valid anymore
        CookidooRequestException
            If the request fails.
        CookidooParseException
            If the parsing of the request response fails.

        """

        url = self.api_endpoint / RECIPE_PATH.format(
            **self._cfg.localization.__dict__, id=id
        )
        result = self._ensure_mapping(
            await self._request_json("get", url, "loading recipe details"),
            "loading recipe details",
        )
        return self._parse_result(
            "loading recipe details",
            lambda: cookidoo_recipe_details_from_json(
                cast(RecipeDetailsJSON, result),
                self._cfg.localization,
            ),
        )

    async def search_recipes(
        self,
        query: str | None = None,
        locale: str | None = None,
        accessories: str | list[str] | None = None,
        languages: str | list[str] | None = None,
        categories: str | list[str] | None = None,
        countries: str | list[str] | None = None,
        ingredients: str | list[str] | None = None,
        exclude_ingredients: str | list[str] | None = None,
        tags: str | list[str] | None = None,
        ratings: str | list[str] | None = None,
        difficulty: str | None = None,
        preparation_time: int | None = None,
        total_time: int | None = None,
        portions: int | None = None,
        page: int | None = None,
        page_size: int | None = None,
        tmv: ThermomixMachineType
        | str
        | list[ThermomixMachineType | str]
        | None = None,
    ) -> CookidooSearchResult:
        """Search recipes in Cookidoo (GET).

        Uses the same API base as the rest of the client (api_endpoint):
        {api_endpoint}/search/{locale}

        Parameters
        ----------
        query
            Optional search query (e.g. "chicken", "pasta").
        locale
            Locale for the search path (e.g. "es", "en", "de").
            Defaults to the first part of the configured language (e.g. "de-CH" -> "de").
        accessories
            Optional comma-separated accessory filters
            (e.g. "includingFriend,includingBladeCover,includingBladeCoverWithPeeler,includingCutter,includingSensor").
        languages
            Optional comma-separated language codes (e.g. "en,es").
        categories
            Optional comma-separated category IDs.
        countries
            Optional comma-separated country codes (e.g. "ar").
        ingredients
            Optional comma-separated ingredients.
        exclude_ingredients
            Optional comma-separated excluded ingredients.
        tags
            Optional comma-separated tags.
        ratings
            Optional comma-separated ratings (e.g. "5,4").
        difficulty
            Optional difficulty (e.g. "easy", "medium", "hard").
        preparation_time
            Optional preparation time in seconds.
        total_time
            Optional total time in seconds.
        portions
            Optional portions count.
        page
            Optional page number (API-dependent, often 0- or 1-based).
        page_size
            Optional page size (API-dependent; common keys: pageSize).
        tmv
            Optional Thermomix machine version. Use ``ThermomixMachineType``
            (e.g. ``ThermomixMachineType.TM7``) or a string ("TM7", "TM6", "TM5").

        Returns
        -------
        CookidooSearchResult
            Search result with recipes and total count.

        Raises
        ------
        CookidooAuthException
            When the access token is not valid anymore.
        CookidooRequestException
            If the request fails.
        CookidooParseException
            If the parsing of the request response fails.

        """
        if locale is None:
            locale = self._cfg.localization.language.split("-")[0]
        url = self.api_endpoint / "search" / locale
        params: dict[str, str] = {}
        if query is not None:
            params["query"] = query
        if accessories is not None and (
            normalized := normalize_list_param(accessories)
        ):
            params["accessories"] = normalized
        if languages is not None and (normalized := normalize_list_param(languages)):
            params["languages"] = normalized
        if categories is not None and (normalized := normalize_list_param(categories)):
            params["categories"] = normalized
        if countries is not None and (normalized := normalize_list_param(countries)):
            params["countries"] = normalized
        if ingredients is not None and (
            normalized := normalize_list_param(ingredients)
        ):
            params["ingredients"] = normalized
        if exclude_ingredients is not None and (
            normalized := normalize_list_param(exclude_ingredients)
        ):
            params["excludeIngredients"] = normalized
        if tags is not None and (normalized := normalize_list_param(tags)):
            params["tags"] = normalized
        if ratings is not None and (normalized := normalize_list_param(ratings)):
            params["ratings"] = normalized
        if difficulty is not None:
            params["difficulty"] = difficulty
        if preparation_time is not None:
            params["preparationTime"] = str(preparation_time)
        if total_time is not None:
            params["totalTime"] = str(total_time)
        if portions is not None:
            params["portions"] = str(portions)
        if page is not None:
            params["page"] = str(page)
        if page_size is not None:
            params["pageSize"] = str(page_size)
        if tmv is not None and (normalized := normalize_tmv_param(tmv)):
            params["tmv"] = normalized
        result = await self._request_json("get", url, "search recipes", params=params)
        if result is None:
            return CookidooSearchResult(recipes=[], total=0)
        if not isinstance(result, dict):
            raise CookidooParseException(
                "Search recipes failed during parsing of request response."
            )
        return cookidoo_search_result_from_json(
            cast(SearchResultJSON, result), self._cfg.localization
        )

    async def get_custom_recipe(self, id: str) -> CookidooCustomRecipe:
        """Get custom recipe.

        Parameters
        ----------
        id
            The id of the custom recipe

        Returns
        -------
        CookidooCustomRecipe
            The custom recipe

        Raises
        ------
        CookidooAuthException
            When the access token is not valid anymore
        CookidooRequestException
            If the request fails.
        CookidooParseException
            If the parsing of the request response fails.

        """

        url = self.api_endpoint / CUSTOM_RECIPE_PATH.format(
            **self._cfg.localization.__dict__, id=id
        )
        result = self._ensure_mapping(
            await self._request_json("get", url, "loading custom recipe"),
            "loading custom recipe",
        )
        return self._parse_result(
            "loading custom recipe",
            lambda: cookidoo_custom_recipe_from_json(
                cast(CustomRecipeJSON, result),
                self._cfg.localization,
            ),
        )

    async def add_custom_recipe_from(
        self, recipeId: str, servingSize: int
    ) -> CookidooCustomRecipe:
        """Add custom recipe.

        Parameters
        ----------
        recipeId
            The base recipe to copy
        servingSize
            The serving size of the custom recipe

        Returns
        -------
        CookidooCustomRecipe
            The added custom recipe

        Raises
        ------
        CookidooAuthException
            When the access token is not valid anymore
        CookidooRequestException
            If the request fails.
        CookidooParseException
            If the parsing of the request response fails.

        """
        json_data = {
            "recipeUrl": str(
                self.api_endpoint
                / RECIPE_PATH.format(**self._cfg.localization.__dict__, id=recipeId)
            ),
            "servingSize": servingSize,
        }
        url = self.api_endpoint / ADD_CUSTOM_RECIPE_PATH.format(
            **self._cfg.localization.__dict__
        )
        result = self._ensure_mapping(
            await self._request_json("post", url, "add custom recipe", json=json_data),
            "add custom recipe",
        )
        return self._parse_result(
            "add custom recipe",
            lambda: cookidoo_custom_recipe_from_json(
                cast(CustomRecipeJSON, result),
                self._cfg.localization,
            ),
        )

    async def remove_custom_recipe(
        self,
        custom_recipe_id: str,
    ) -> None:
        """Remove custom recipe.

        Parameters
        ----------
        custom_recipe_id
            The custom recipe id to remove

        Raises
        ------
        CookidooAuthException
            When the access token is not valid anymore
        CookidooRequestException
            If the request fails.
        CookidooParseException
            If the parsing of the request response fails.

        """
        url = self.api_endpoint / REMOVE_CUSTOM_RECIPE_PATH.format(
            **self._cfg.localization.__dict__, id=custom_recipe_id
        )
        await self._request_json(
            "delete", url, "remove custom recipe", parse_response=False
        )

    async def get_shopping_list_recipes(
        self,
    ) -> list[CookidooShoppingRecipe]:
        """Get recipes.

        Returns
        -------
        list[CookidooShoppingRecipe]
            The list of the recipes

        Raises
        ------
        CookidooAuthException
            When the access token is not valid anymore
        CookidooRequestException
            If the request fails.
        CookidooParseException
            If the parsing of the request response fails.

        """

        url = self.api_endpoint / SHOPPING_LIST_RECIPES_PATH.format(
            **self._cfg.localization.__dict__
        )
        result = self._ensure_mapping(
            await self._request_json("get", url, "loading recipes"),
            "loading recipes",
        )
        return self._parse_result(
            "loading recipes",
            lambda: [
                cookidoo_recipe_from_json(
                    cast(RecipeJSON, recipe), self._cfg.localization
                )
                for recipe in [
                    *cast(Sequence[object], result["recipes"]),
                    *cast(Sequence[object], result["customerRecipes"]),
                ]
            ],
        )

    async def get_ingredient_items(
        self,
    ) -> list[CookidooIngredientItem]:
        """Get ingredient items.

        Returns
        -------
        list[CookidooIngredientItem]
            The list of the ingredient items

        Raises
        ------
        CookidooAuthException
            When the access token is not valid anymore
        CookidooRequestException
            If the request fails.
        CookidooParseException
            If the parsing of the request response fails.

        """

        url = self.api_endpoint / INGREDIENT_ITEMS_PATH.format(
            **self._cfg.localization.__dict__
        )
        result = self._ensure_mapping(
            await self._request_json("get", url, "loading ingredient items"),
            "loading ingredient items",
        )
        return self._parse_result(
            "loading ingredient items",
            lambda: [
                cookidoo_ingredient_item_from_json(cast(ItemJSON, ingredient))
                for recipe in [
                    *cast(Sequence[Mapping[str, object]], result["recipes"]),
                    *cast(Sequence[Mapping[str, object]], result["customerRecipes"]),
                ]
                for ingredient in cast(
                    Sequence[object], recipe["recipeIngredientGroups"]
                )
            ],
        )

    async def add_ingredient_items_for_recipes(
        self,
        recipe_ids: list[str],
    ) -> list[CookidooIngredientItem]:
        """Add ingredient items for recipes.

        Parameters
        ----------
        recipe_ids
            The recipe ids for the ingredient items to add to the shopping list

        Returns
        -------
        list[CookidooIngredientItem]
            The list of the added ingredient items

        Raises
        ------
        CookidooAuthException
            When the access token is not valid anymore
        CookidooRequestException
            If the request fails.
        CookidooParseException
            If the parsing of the request response fails.

        """
        json_data = {"recipeIDs": recipe_ids}
        url = self.api_endpoint / ADD_INGREDIENT_ITEMS_FOR_RECIPES_PATH.format(
            **self._cfg.localization.__dict__
        )
        result = self._ensure_mapping(
            await self._request_json(
                "post", url, "add ingredient items for recipes", json=json_data
            ),
            "add ingredient items for recipes",
        )
        return self._parse_result(
            "loading added ingredient items",
            lambda: [
                cookidoo_ingredient_item_from_json(cast(ItemJSON, ingredient))
                for recipe in cast(Sequence[Mapping[str, object]], result["data"])
                for ingredient in cast(
                    Sequence[object], recipe["recipeIngredientGroups"]
                )
            ],
        )

    async def remove_ingredient_items_for_recipes(
        self,
        recipe_ids: list[str],
    ) -> None:
        """Remove ingredient items for recipes.

        Parameters
        ----------
        recipe_ids
            The recipe ids for the ingredient items to remove to the shopping list

        Raises
        ------
        CookidooAuthException
            When the access token is not valid anymore
        CookidooRequestException
            If the request fails.
        CookidooParseException
            If the parsing of the request response fails.

        """
        json_data = {"recipeIDs": recipe_ids}
        url = self.api_endpoint / REMOVE_INGREDIENT_ITEMS_FOR_RECIPES_PATH.format(
            **self._cfg.localization.__dict__
        )
        await self._request_json(
            "post",
            url,
            "remove ingredient items for recipes",
            json=json_data,
            parse_response=False,
        )

    async def edit_ingredient_items_ownership(
        self,
        ingredient_items: list[CookidooIngredientItem],
    ) -> list[CookidooIngredientItem]:
        """Edit ownership ingredient items.

        Parameters
        ----------
        ingredient_items
            The ingredient items to change the the `is_owned` value for

        Returns
        -------
        list[CookidooIngredientItem]
            The list of the edited ingredient items

        Raises
        ------
        CookidooAuthException
            When the access token is not valid anymore
        CookidooRequestException
            If the request fails.
        CookidooParseException
            If the parsing of the request response fails.

        """
        json_data = {
            "ingredients": [
                {
                    "id": ingredient_item.id,
                    "isOwned": ingredient_item.is_owned,
                    "ownedTimestamp": int(time.time()),
                }
                for ingredient_item in ingredient_items
            ]
        }
        url = self.api_endpoint / EDIT_OWNERSHIP_INGREDIENT_ITEMS_PATH.format(
            **self._cfg.localization.__dict__
        )
        result = self._ensure_mapping(
            await self._request_json(
                "post", url, "edit ingredient items ownership", json=json_data
            ),
            "edit ingredient items ownership",
        )
        return self._parse_result(
            "loading edited ingredient items",
            lambda: [
                cookidoo_ingredient_item_from_json(cast(ItemJSON, ingredient))
                for ingredient in cast(Sequence[object], result["data"])
            ],
        )

    async def add_ingredient_items_for_custom_recipes(
        self,
        recipe_ids: list[str],
    ) -> list[CookidooIngredientItem]:
        """Add ingredient items for custom recipes.

        Parameters
        ----------
        recipe_ids
            The recipe ids for the ingredient items to add to the shopping list

        Returns
        -------
        list[CookidooIngredientItem]
            The list of the added ingredient items

        Raises
        ------
        CookidooAuthException
            When the access token is not valid anymore
        CookidooRequestException
            If the request fails.
        CookidooParseException
            If the parsing of the request response fails.

        """
        json_data = {
            "recipeIDs": [
                {"id": recipe_id, "source": "CUSTOMER"} for recipe_id in recipe_ids
            ]
        }
        url = self.api_endpoint / ADD_INGREDIENT_ITEMS_FOR_RECIPES_PATH.format(
            **self._cfg.localization.__dict__
        )
        result = self._ensure_mapping(
            await self._request_json(
                "post", url, "add ingredient items for custom recipes", json=json_data
            ),
            "add ingredient items for custom recipes",
        )
        return self._parse_result(
            "loading added ingredient items",
            lambda: [
                cookidoo_ingredient_item_from_json(cast(ItemJSON, ingredient))
                for recipe in cast(Sequence[Mapping[str, object]], result["data"])
                for ingredient in cast(
                    Sequence[object], recipe["recipeIngredientGroups"]
                )
            ],
        )

    async def remove_ingredient_items_for_custom_recipes(
        self,
        recipe_ids: list[str],
    ) -> None:
        """Remove ingredient items for custom recipes.

        Parameters
        ----------
        recipe_ids
            The custom recipe ids for the ingredient items to remove to the shopping list

        Raises
        ------
        CookidooAuthException
            When the access token is not valid anymore
        CookidooRequestException
            If the request fails.
        CookidooParseException
            If the parsing of the request response fails.

        """
        json_data = {"recipeIDs": recipe_ids}
        url = self.api_endpoint / REMOVE_INGREDIENT_ITEMS_FOR_RECIPES_PATH.format(
            **self._cfg.localization.__dict__
        )
        await self._request_json(
            "post",
            url,
            "remove ingredient items for custom recipes",
            json=json_data,
            parse_response=False,
        )

    async def get_additional_items(
        self,
    ) -> list[CookidooAdditionalItem]:
        """Get additional items.

        Returns
        -------
        list[CookidooAdditionalItem]
            The list of the additional items

        Raises
        ------
        CookidooAuthException
            When the access token is not valid anymore
        CookidooRequestException
            If the request fails.
        CookidooParseException
            If the parsing of the request response fails.

        """

        url = self.api_endpoint / ADDITIONAL_ITEMS_PATH.format(
            **self._cfg.localization.__dict__
        )
        result = self._ensure_mapping(
            await self._request_json("get", url, "loading additional items"),
            "loading additional items",
        )
        return self._parse_result(
            "loading additional items",
            lambda: [
                cookidoo_additional_item_from_json(
                    cast(AdditionalItemJSON, additional_item)
                )
                for additional_item in cast(Sequence[object], result["additionalItems"])
            ],
        )

    async def add_additional_items(
        self,
        additional_item_names: list[str],
    ) -> list[CookidooAdditionalItem]:
        """Create additional items.

        Parameters
        ----------
        additional_item_names
            The additional item names to create, only the label can be set, as the default state `is_owned=false` is forced (chain with immediate update call for work-around)

        Returns
        -------
        list[CookidooAdditionalItem]
            The list of the added additional items

        Raises
        ------
        CookidooAuthException
            When the access token is not valid anymore
        CookidooRequestException
            If the request fails.
        CookidooParseException
            If the parsing of the request response fails.

        """
        json_data = {"itemsValue": additional_item_names}
        url = self.api_endpoint / ADD_ADDITIONAL_ITEMS_PATH.format(
            **self._cfg.localization.__dict__
        )
        result = self._ensure_mapping(
            await self._request_json(
                "post", url, "add additional items", json=json_data
            ),
            "add additional items",
        )
        return self._parse_result(
            "loading added additional items",
            lambda: [
                cookidoo_additional_item_from_json(
                    cast(AdditionalItemJSON, additional_item)
                )
                for additional_item in cast(Sequence[object], result["data"])
            ],
        )

    async def edit_additional_items(
        self,
        additional_items: list[CookidooAdditionalItem],
    ) -> list[CookidooAdditionalItem]:
        """Edit additional items.

        Parameters
        ----------
        additional_items
            The additional items to change the the `name` value for

        Returns
        -------
        list[CookidooAdditionalItem]
            The list of the edited additional items

        Raises
        ------
        CookidooAuthException
            When the access token is not valid anymore
        CookidooRequestException
            If the request fails.
        CookidooParseException
            If the parsing of the request response fails.

        """
        json_data = {
            "additionalItems": [
                {
                    "id": additional_item.id,
                    "name": additional_item.name,
                }
                for additional_item in additional_items
            ]
        }
        url = self.api_endpoint / EDIT_ADDITIONAL_ITEMS_PATH.format(
            **self._cfg.localization.__dict__
        )
        result = self._ensure_mapping(
            await self._request_json(
                "post", url, "edit additional items", json=json_data
            ),
            "edit additional items",
        )
        return self._parse_result(
            "loading edited additional items",
            lambda: [
                cookidoo_additional_item_from_json(
                    cast(AdditionalItemJSON, additional_item)
                )
                for additional_item in cast(Sequence[object], result["data"])
            ],
        )

    async def edit_additional_items_ownership(
        self,
        additional_items: list[CookidooAdditionalItem],
    ) -> list[CookidooAdditionalItem]:
        """Edit ownership additional items.

        Parameters
        ----------
        additional_items
            The additional items to change the the `is_owned` value for

        Returns
        -------
        list[CookidooAdditionalItem]
            The list of the edited additional items

        Raises
        ------
        CookidooAuthException
            When the access token is not valid anymore
        CookidooRequestException
            If the request fails.
        CookidooParseException
            If the parsing of the request response fails.

        """
        json_data = {
            "additionalItems": [
                {
                    "id": additional_item.id,
                    "isOwned": additional_item.is_owned,
                    "ownedTimestamp": int(time.time()),
                }
                for additional_item in additional_items
            ]
        }
        url = self.api_endpoint / EDIT_OWNERSHIP_ADDITIONAL_ITEMS_PATH.format(
            **self._cfg.localization.__dict__
        )
        result = self._ensure_mapping(
            await self._request_json(
                "post", url, "edit additional items ownership", json=json_data
            ),
            "edit additional items ownership",
        )
        return self._parse_result(
            "loading edited additional items",
            lambda: [
                cookidoo_additional_item_from_json(
                    cast(AdditionalItemJSON, additional_item)
                )
                for additional_item in cast(Sequence[object], result["data"])
            ],
        )

    async def remove_additional_items(
        self,
        additional_item_ids: list[str],
    ) -> None:
        """Remove additional items.

        Parameters
        ----------
        additional_item_ids
            The additional item ids to remove

        Raises
        ------
        CookidooAuthException
            When the access token is not valid anymore
        CookidooRequestException
            If the request fails.
        CookidooParseException
            If the parsing of the request response fails.

        """
        json_data = {"additionalItemIDs": additional_item_ids}
        url = self.api_endpoint / REMOVE_ADDITIONAL_ITEMS_PATH.format(
            **self._cfg.localization.__dict__
        )
        await self._request_json(
            "post",
            url,
            "remove additional items",
            json=json_data,
            parse_response=False,
        )

    async def clear_shopping_list(
        self,
    ) -> None:
        """Remove all additional items, ingredients and recipes.

        Raises
        ------
        CookidooAuthException
            When the access token is not valid anymore
        CookidooRequestException
            If the request fails.
        CookidooParseException
            If the parsing of the request response fails.

        """
        url = self.api_endpoint / INGREDIENT_ITEMS_PATH.format(
            **self._cfg.localization.__dict__
        )
        await self._request_json(
            "delete", url, "clear shopping list", parse_response=False
        )

    async def count_managed_collections(self) -> tuple[int, int]:
        """Get managed collections.

        Returns
        -------
        tuple[int, int]
            The number of managed collections and the number of pages

        Raises
        ------
        CookidooAuthException
            When the access token is not valid anymore
        CookidooRequestException
            If the request fails.
        CookidooParseException
            If the parsing of the request response fails.

        """

        url = self.api_endpoint / MANAGED_COLLECTIONS_PATH.format(
            **self._cfg.localization.__dict__
        )
        result = self._ensure_mapping(
            await self._request_json(
                "get",
                url,
                "loading managed collections",
                headers={"ACCEPT": MANAGED_COLLECTIONS_PATH_ACCEPT},
            ),
            "loading managed collections",
        )
        return self._parse_result(
            "loading managed collections",
            lambda: (
                cast(PaginationJSON, result["page"])["totalElements"],
                cast(PaginationJSON, result["page"])["totalPages"],
            ),
        )

    async def get_managed_collections(self, page: int = 0) -> list[CookidooCollection]:
        """Get managed collections.

        Parameters
        ----------
        page
            The page of the managed collections

        Returns
        -------
        list[CookidooCollection]
            The list of the managed collections

        Raises
        ------
        CookidooAuthException
            When the access token is not valid anymore
        CookidooRequestException
            If the request fails.
        CookidooParseException
            If the parsing of the request response fails.

        """

        url = self.api_endpoint / MANAGED_COLLECTIONS_PATH.format(
            **self._cfg.localization.__dict__
        )
        result = self._ensure_mapping(
            await self._request_json(
                "get",
                url,
                "loading managed collections",
                params={"page": str(page)},
                headers={"ACCEPT": MANAGED_COLLECTIONS_PATH_ACCEPT},
            ),
            "loading managed collections",
        )
        return self._parse_result(
            "loading managed collections",
            lambda: [
                cookidoo_collection_from_json(cast(ManagedCollectionJSON, item))
                for item in cast(Sequence[object], result["managedlists"])
            ],
        )

    async def add_managed_collection(
        self,
        managed_collection_id: str,
    ) -> CookidooCollection:
        """Add managed collections.

        Parameters
        ----------
        managed_collection_id
            The managed collection id to add

        Returns
        -------
        CookidooCollection
            The added managed collection

        Raises
        ------
        CookidooAuthException
            When the access token is not valid anymore
        CookidooRequestException
            If the request fails.
        CookidooParseException
            If the parsing of the request response fails.

        """
        json_data = {"collectionId": managed_collection_id}
        url = self.api_endpoint / ADD_MANAGED_COLLECTION_PATH.format(
            **self._cfg.localization.__dict__
        )
        result = self._ensure_mapping(
            await self._request_json(
                "post",
                url,
                "add managed collection",
                json=json_data,
                headers={"ACCEPT": MANAGED_COLLECTIONS_PATH_ACCEPT},
            ),
            "add managed collection",
        )
        return self._parse_result(
            "loading added managed collection",
            lambda: cookidoo_collection_from_json(
                cast(ManagedCollectionJSON, result["content"])
            ),
        )

    async def remove_managed_collection(
        self,
        managed_collection_id: str,
    ) -> None:
        """Remove managed collection.

        Parameters
        ----------
        managed_collection_id
            The managed collection id to remove

        Raises
        ------
        CookidooAuthException
            When the access token is not valid anymore
        CookidooRequestException
            If the request fails.
        CookidooParseException
            If the parsing of the request response fails.

        """
        url = self.api_endpoint / REMOVE_MANAGED_COLLECTION_PATH.format(
            **self._cfg.localization.__dict__, id=managed_collection_id
        )
        await self._request_json(
            "delete",
            url,
            "remove managed collection",
            headers={"ACCEPT": MANAGED_COLLECTIONS_PATH_ACCEPT},
            parse_response=False,
        )

    async def count_custom_collections(self) -> tuple[int, int]:
        """Get custom collections.

        Returns
        -------
        tuple[int, int]
            The number of custom collections and the number of pages

        Raises
        ------
        CookidooAuthException
            When the access token is not valid anymore
        CookidooRequestException
            If the request fails.
        CookidooParseException
            If the parsing of the request response fails.

        """

        url = self.api_endpoint / CUSTOM_COLLECTIONS_PATH.format(
            **self._cfg.localization.__dict__
        )
        result = self._ensure_mapping(
            await self._request_json(
                "get",
                url,
                "loading custom collections",
                headers={"ACCEPT": CUSTOM_COLLECTIONS_PATH_ACCEPT},
            ),
            "loading custom collections",
        )
        return self._parse_result(
            "loading custom collections",
            lambda: (
                cast(PaginationJSON, result["page"])["totalElements"],
                cast(PaginationJSON, result["page"])["totalPages"],
            ),
        )

    async def get_custom_collections(self, page: int = 0) -> list[CookidooCollection]:
        """Get custom collections.

        Parameters
        ----------
        page
            The page of the custom collections

        Returns
        -------
        list[CookidooCollection]
            The list of the custom collections

        Raises
        ------
        CookidooAuthException
            When the access token is not valid anymore
        CookidooRequestException
            If the request fails.
        CookidooParseException
            If the parsing of the request response fails.

        """

        url = self.api_endpoint / CUSTOM_COLLECTIONS_PATH.format(
            **self._cfg.localization.__dict__
        )
        result = self._ensure_mapping(
            await self._request_json(
                "get",
                url,
                "loading custom collections",
                params={"page": str(page)},
                headers={"ACCEPT": CUSTOM_COLLECTIONS_PATH_ACCEPT},
            ),
            "loading custom collections",
        )
        return self._parse_result(
            "loading custom collections",
            lambda: [
                cookidoo_collection_from_json(cast(CustomCollectionJSON, item))
                for item in cast(Sequence[object], result["customlists"])
            ],
        )

    async def add_custom_collection(
        self,
        custom_collection_name: str,
    ) -> CookidooCollection:
        """Add custom collections.

        Parameters
        ----------
        custom_collection_name
            The custom collection name to add

        Returns
        -------
        CookidooCollection
            The added custom collection

        Raises
        ------
        CookidooAuthException
            When the access token is not valid anymore
        CookidooRequestException
            If the request fails.
        CookidooParseException
            If the parsing of the request response fails.

        """
        json_data = {"title": custom_collection_name}
        url = self.api_endpoint / ADD_CUSTOM_COLLECTION_PATH.format(
            **self._cfg.localization.__dict__
        )
        result = self._ensure_mapping(
            await self._request_json(
                "post",
                url,
                "add custom collection",
                json=json_data,
                headers={"ACCEPT": CUSTOM_COLLECTIONS_PATH_ACCEPT},
            ),
            "add custom collection",
        )
        return self._parse_result(
            "loading added custom collection",
            lambda: cookidoo_collection_from_json(
                cast(CustomCollectionJSON, result["content"])
            ),
        )

    async def remove_custom_collection(
        self,
        custom_collection_id: str,
    ) -> None:
        """Remove custom collection.

        Parameters
        ----------
        custom_collection_id
            The custom collection id to remove

        Raises
        ------
        CookidooAuthException
            When the access token is not valid anymore
        CookidooRequestException
            If the request fails.
        CookidooParseException
            If the parsing of the request response fails.

        """
        url = self.api_endpoint / REMOVE_CUSTOM_COLLECTION_PATH.format(
            **self._cfg.localization.__dict__, id=custom_collection_id
        )
        await self._request_json(
            "delete",
            url,
            "remove custom collection",
            headers={"ACCEPT": CUSTOM_COLLECTIONS_PATH_ACCEPT},
            parse_response=False,
        )

    async def add_recipes_to_custom_collection(
        self,
        custom_collection_id: str,
        recipe_ids: list[str],
    ) -> CookidooCollection:
        """Add recipes to a custom collections.

        Parameters
        ----------
        custom_collection_id
            The custom collection to add the recipes to
        recipe_ids
            The recipe ids to add to a custom collection

        Returns
        -------
        CookidooCollection
            The changed custom collection

        Raises
        ------
        CookidooAuthException
            When the access token is not valid anymore
        CookidooRequestException
            If the request fails.
        CookidooParseException
            If the parsing of the request response fails.

        """
        json_data = {"recipeIds": recipe_ids}
        url = self.api_endpoint / ADD_RECIPES_TO_CUSTOM_COLLECTION_PATH.format(
            **self._cfg.localization.__dict__, id=custom_collection_id
        )
        result = self._ensure_mapping(
            await self._request_json(
                "put", url, "add recipes to custom collection", json=json_data
            ),
            "add recipes to custom collection",
        )
        return self._parse_result(
            "loading added recipes",
            lambda: cookidoo_collection_from_json(
                cast(CustomCollectionJSON, result["content"])
            ),
        )

    async def remove_recipe_from_custom_collection(
        self,
        custom_collection_id: str,
        recipe_id: str,
    ) -> CookidooCollection:
        """Remove recipe from a custom collections.

        Parameters
        ----------
        custom_collection_id
            The custom collection to remove the recipe from
        recipe_id
            The recipe id to remove from a custom collection

        Returns
        -------
        CookidooCollection
            The changed custom collection

        Raises
        ------
        CookidooAuthException
            When the access token is not valid anymore
        CookidooRequestException
            If the request fails.
        CookidooParseException
            If the parsing of the request response fails.

        """
        url = self.api_endpoint / REMOVE_RECIPE_FROM_CUSTOM_COLLECTION_PATH.format(
            **self._cfg.localization.__dict__,
            id=custom_collection_id,
            recipe=recipe_id,
        )
        result = self._ensure_mapping(
            await self._request_json(
                "delete", url, "remove recipe from custom collection"
            ),
            "remove recipe from custom collection",
        )
        return self._parse_result(
            "loading removed recipe",
            lambda: cookidoo_collection_from_json(
                cast(CustomCollectionJSON, result["content"])
            ),
        )

    async def get_recipes_in_calendar_week(
        self, day: date
    ) -> list[CookidooCalendarDay]:
        """Get recipes in a calendar week.

        Parameters
        ----------
        day
            The date specifying the calendar week

        Returns
        -------
        list[CookidooCalendarDay]
            The list of the calendar days with recipes

        Raises
        ------
        CookidooAuthException
            When the access token is not valid anymore
        CookidooRequestException
            If the request fails.
        CookidooParseException
            If the parsing of the request response fails.

        """

        url = self.api_endpoint / RECIPES_IN_CALENDAR_WEEK_PATH.format(
            **self._cfg.localization.__dict__, day=day.isoformat()
        )
        result = self._ensure_mapping(
            await self._request_json("get", url, "loading recipes in calendar week"),
            "loading recipes in calendar week",
        )
        return self._parse_result(
            "loading recipes in calendar week",
            lambda: [
                cookidoo_calendar_day_from_json(
                    cast(CalendarDayJSON, calendar_day), self._cfg.localization
                )
                for calendar_day in cast(Sequence[object], result["myDays"])
            ],
        )

    async def add_recipes_to_calendar(
        self,
        day: date,
        recipe_ids: list[str],
    ) -> CookidooCalendarDay:
        """Add recipes to a calendar.

        Parameters
        ----------
        day
            The date to add the recipes to in the calendar
        recipe_ids
            The recipe ids to add to the calendar

        Returns
        -------
        CookidooCalendarDay
            The changed calendar day

        Raises
        ------
        CookidooAuthException
            When the access token is not valid anymore
        CookidooRequestException
            If the request fails.
        CookidooParseException
            If the parsing of the request response fails.

        """
        json_data = {"recipeIds": recipe_ids, "dayKey": day.isoformat()}
        url = self.api_endpoint / ADD_RECIPES_TO_CALENDER_PATH.format(
            **self._cfg.localization.__dict__
        )
        result = self._ensure_mapping(
            await self._request_json(
                "put", url, "add recipes to calendar", json=json_data
            ),
            "add recipes to calendar",
        )
        return self._parse_result(
            "loading added recipes",
            lambda: cookidoo_calendar_day_from_json(
                cast(CalendarDayJSON, result["content"]),
                self._cfg.localization,
            ),
        )

    async def remove_recipe_from_calendar(
        self,
        day: date,
        recipe_id: str,
    ) -> CookidooCalendarDay:
        """Remove recipe from calendar.

        Parameters
        ----------
        day
            The date to remove the recipe from in the calendar
        recipe_id
            The recipe id to remove from the calendar

        Returns
        -------
        CookidooCalendarDay
            The changed calendar day

        Raises
        ------
        CookidooAuthException
            When the access token is not valid anymore
        CookidooRequestException
            If the request fails.
        CookidooParseException
            If the parsing of the request response fails.

        """
        url = self.api_endpoint / REMOVE_RECIPE_FROM_CALENDER_PATH.format(
            **self._cfg.localization.__dict__,
            day=day.isoformat(),
            recipe=recipe_id,
        )
        result = self._ensure_mapping(
            await self._request_json("delete", url, "remove recipe from calendar"),
            "remove recipe from calendar",
        )
        return self._parse_result(
            "loading removed recipe",
            lambda: cookidoo_calendar_day_from_json(
                cast(CalendarDayJSON, result["content"]),
                self._cfg.localization,
            ),
        )

    async def add_custom_recipes_to_calendar(
        self,
        day: date,
        recipe_ids: list[str],
    ) -> CookidooCalendarDay:
        """Add custom recipes to a calendar.

        Parameters
        ----------
        day
            The date to add the custom recipes to in the calendar
        recipe_ids
            The recipe ids to add to the calendar

        Returns
        -------
        CookidooCalendarDay
            The changed calendar day

        Raises
        ------
        CookidooAuthException
            When the access token is not valid anymore
        CookidooRequestException
            If the request fails.
        CookidooParseException
            If the parsing of the request response fails.

        """
        json_data = {
            "recipeIds": recipe_ids,
            "dayKey": day.isoformat(),
            "recipeSource": "CUSTOMER",
        }
        url = self.api_endpoint / ADD_RECIPES_TO_CALENDER_PATH.format(
            **self._cfg.localization.__dict__
        )
        result = self._ensure_mapping(
            await self._request_json(
                "put", url, "add custom recipes to calendar", json=json_data
            ),
            "add custom recipes to calendar",
        )
        return self._parse_result(
            "loading added custom recipes",
            lambda: cookidoo_calendar_day_from_json(
                cast(CalendarDayJSON, result["content"]),
                self._cfg.localization,
            ),
        )

    async def remove_custom_recipe_from_calendar(
        self,
        day: date,
        recipe_id: str,
    ) -> CookidooCalendarDay:
        """Remove custom recipe from calendar.

        Parameters
        ----------
        day
            The date to remove the custom recipe from in the calendar
        recipe_id
            The custom recipe id to remove from the calendar

        Returns
        -------
        CookidooCalendarDay
            The changed calendar day

        Raises
        ------
        CookidooAuthException
            When the access token is not valid anymore
        CookidooRequestException
            If the request fails.
        CookidooParseException
            If the parsing of the request response fails.

        """
        url = self.api_endpoint / REMOVE_RECIPE_FROM_CALENDER_PATH.format(
            **self._cfg.localization.__dict__,
            day=day.isoformat(),
            recipe=recipe_id,
        )
        result = self._ensure_mapping(
            await self._request_json(
                "delete",
                url,
                "remove custom recipe from calendar",
                params={"recipeSource": "CUSTOMER"},
            ),
            "remove custom recipe from calendar",
        )
        return self._parse_result(
            "loading custom removed recipe",
            lambda: cookidoo_calendar_day_from_json(
                cast(CalendarDayJSON, result["content"]),
                self._cfg.localization,
            ),
        )
