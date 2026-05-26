"""Cookidoo api implementation."""

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
from typing import Any, cast
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
    CustomCollectionJSON,
    CustomRecipeJSON,
    ItemJSON,
    ManagedCollectionJSON,
    RecipeDetailsJSON,
    RecipeJSON,
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

    async def _request(
        self,
        method: str,
        url: URL,
        operation: str,
        *,
        json: dict[str, Any] | list[Any] | None = None,
        headers: dict[str, str] | None = None,
        accepted_statuses: tuple[HTTPStatus, ...] = (HTTPStatus.OK,),
    ) -> dict[str, Any] | None:
        """Execute an HTTP request with standard error handling."""
        merged_headers = {**self._api_headers, **(headers or {})}

        try:
            async with self._session.request(
                method, url, headers=merged_headers, json=json
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
                try:
                    return cast(dict[str, Any], await r.json())
                except (JSONDecodeError, KeyError) as e:
                    _LOGGER.debug(
                        "Exception: Cannot parse %s response:\n%s",
                        operation,
                        traceback.format_exc(),
                    )
                    raise CookidooParseException(
                        f"{operation.capitalize()} failed during parsing of request response."
                    ) from e

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

        try:
            url = self.api_endpoint / COMMUNITY_PROFILE_PATH.format(
                **self._cfg.localization.__dict__
            )
            async with self._session.get(url, headers=self._api_headers) as r:
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
                            "Exception: Cannot get user info: %s",
                            errmsg["error_description"],
                        )
                    raise CookidooAuthException(
                        "Loading user info failed due to authorization failure, "
                        "the authorization token is invalid or expired."
                    )

                r.raise_for_status()

                try:
                    return cookidoo_user_info_from_json(await r.json())
                except (JSONDecodeError, KeyError) as e:
                    _LOGGER.debug(
                        "Exception: Cannot get user info:\n%s",
                        traceback.format_exc(),
                    )
                    raise CookidooParseException(
                        "Loading user info failed during parsing of request response."
                    ) from e
        except TimeoutError as e:
            _LOGGER.debug(
                "Exception: Cannot get user info:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Loading user info failed due to connection timeout."
            ) from e
        except ClientError as e:
            _LOGGER.debug(
                "Exception: Cannot user info:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Loading user info failed due to request exception."
            ) from e

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

        try:
            url = self.api_endpoint / SUBSCRIPTIONS_PATH.format(
                **self._cfg.localization.__dict__
            )
            async with self._session.get(url, headers=self._api_headers) as r:
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
                            "Exception: Cannot get active subscription: %s",
                            errmsg["error_description"],
                        )
                    raise CookidooAuthException(
                        "Loading active subscription failed due to authorization failure, "
                        "the authorization token is invalid or expired."
                    )

                r.raise_for_status()

                try:
                    if subscription := next(
                        (
                            subscription
                            for subscription in (await r.json())
                            if subscription["active"]
                        ),
                        None,
                    ):
                        return cookidoo_subscription_from_json(subscription)
                    else:
                        return None

                except (JSONDecodeError, KeyError) as e:
                    _LOGGER.debug(
                        "Exception: Cannot get active subscription:\n%s",
                        traceback.format_exc(),
                    )
                    raise CookidooParseException(
                        "Loading active subscription failed during parsing of request response."
                    ) from e
        except TimeoutError as e:
            _LOGGER.debug(
                "Exception: Cannot get active subscription:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Loading user info failed due to connection timeout."
            ) from e
        except ClientError as e:
            _LOGGER.debug(
                "Exception: Cannot active subscription:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Loading active subscription failed due to request exception."
            ) from e

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

        try:
            url = self.api_endpoint / RECIPE_PATH.format(
                **self._cfg.localization.__dict__, id=id
            )
            async with self._session.get(url, headers=self._api_headers) as r:
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
                            "Exception: Cannot get recipe details: %s",
                            errmsg["error_description"],
                        )
                    raise CookidooAuthException(
                        "Loading recipe details failed due to authorization failure, "
                        "the authorization token is invalid or expired."
                    )

                r.raise_for_status()

                try:
                    return cookidoo_recipe_details_from_json(
                        cast(RecipeDetailsJSON, await r.json()),
                        self._cfg.localization,
                    )

                except (JSONDecodeError, KeyError) as e:
                    _LOGGER.debug(
                        "Exception: Cannot get recipe details:\n%s",
                        traceback.format_exc(),
                    )
                    raise CookidooParseException(
                        "Loading recipe details failed during parsing of request response."
                    ) from e
        except TimeoutError as e:
            _LOGGER.debug(
                "Exception: Cannot get recipe details:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Loading recipe details failed due to connection timeout."
            ) from e
        except ClientError as e:
            _LOGGER.debug(
                "Exception: Cannot recipe details:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Loading recipe details failed due to request exception."
            ) from e

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
        url = url.with_query(params)
        result = await self._request(
            "get", url, "search recipes", accepted_statuses=(HTTPStatus.OK,)
        )
        if result is None:
            return CookidooSearchResult(recipes=[], total=0)
        return cookidoo_search_result_from_json(result, self._cfg.localization)

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

        try:
            url = self.api_endpoint / CUSTOM_RECIPE_PATH.format(
                **self._cfg.localization.__dict__, id=id
            )
            async with self._session.get(url, headers=self._api_headers) as r:
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
                            "Exception: Cannot get custom recipe: %s",
                            errmsg["error_description"],
                        )
                    raise CookidooAuthException(
                        "Loading custom recipe failed due to authorization failure, "
                        "the authorization token is invalid or expired."
                    )

                r.raise_for_status()

                try:
                    return cookidoo_custom_recipe_from_json(
                        cast(CustomRecipeJSON, await r.json()),
                        self._cfg.localization,
                    )

                except (JSONDecodeError, KeyError) as e:
                    _LOGGER.debug(
                        "Exception: Cannot get custom recipe:\n%s",
                        traceback.format_exc(),
                    )
                    raise CookidooParseException(
                        "Loading custom recipe failed during parsing of request response."
                    ) from e
        except TimeoutError as e:
            _LOGGER.debug(
                "Exception: Cannot get custom recipe:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Loading custom recipe failed due to connection timeout."
            ) from e
        except ClientError as e:
            _LOGGER.debug(
                "Exception: Cannot custom recipe:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Loading custom recipe failed due to request exception."
            ) from e

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
        try:
            url = self.api_endpoint / ADD_CUSTOM_RECIPE_PATH.format(
                **self._cfg.localization.__dict__
            )
            async with self._session.post(
                url,
                headers={
                    **self._api_headers,
                },
                json=json_data,
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
                            "Exception: Cannot add custom recipe: %s",
                            errmsg["error_description"],
                        )
                    raise CookidooAuthException(
                        "Add custom recipe failed due to authorization failure, "
                        "the authorization token is invalid or expired."
                    )

                r.raise_for_status()
                try:
                    return cookidoo_custom_recipe_from_json(
                        cast(CustomRecipeJSON, await r.json()),
                        self._cfg.localization,
                    )

                except (JSONDecodeError, KeyError) as e:
                    _LOGGER.debug(
                        "Exception: Cannot get added custom recipe:\n%s",
                        traceback.format_exc(),
                    )
                    raise CookidooParseException(
                        "Loading added custom recipe failed during parsing of request response."
                    ) from e
        except TimeoutError as e:
            _LOGGER.debug(
                "Exception: Cannot execute add custom recipe:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Add custom recipe failed due to connection timeout."
            ) from e
        except ClientError as e:
            _LOGGER.debug(
                "Exception: Cannot execute add custom recipe:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Add custom recipe failed due to request exception."
            ) from e

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
        try:
            url = self.api_endpoint / REMOVE_CUSTOM_RECIPE_PATH.format(
                **self._cfg.localization.__dict__, id=custom_recipe_id
            )
            async with self._session.delete(
                url,
                headers={
                    **self._api_headers,
                },
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
                            "Exception: Cannot remove custom recipe: %s",
                            errmsg["error_description"],
                        )
                    raise CookidooAuthException(
                        "Remove custom recipe failed due to authorization failure, "
                        "the authorization token is invalid or expired."
                    )

                r.raise_for_status()
        except TimeoutError as e:
            _LOGGER.debug(
                "Exception: Cannot execute remove custom recipe:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Remove custom recipe failed due to connection timeout."
            ) from e
        except ClientError as e:
            _LOGGER.debug(
                "Exception: Cannot execute remove custom recipe:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Remove custom recipe failed due to request exception."
            ) from e

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

        try:
            url = self.api_endpoint / SHOPPING_LIST_RECIPES_PATH.format(
                **self._cfg.localization.__dict__
            )
            async with self._session.get(url, headers=self._api_headers) as r:
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
                            "Exception: Cannot get recipes: %s",
                            errmsg["error_description"],
                        )
                    raise CookidooAuthException(
                        "Loading recipes failed due to authorization failure, "
                        "the authorization token is invalid or expired."
                    )

                r.raise_for_status()

                try:
                    _d = await r.json()
                    return [
                        cookidoo_recipe_from_json(
                            cast(RecipeJSON, recipe), self._cfg.localization
                        )
                        for recipe in [*_d["recipes"], *_d["customerRecipes"]]
                    ]

                except (JSONDecodeError, KeyError) as e:
                    _LOGGER.debug(
                        "Exception: Cannot get recipes:\n%s",
                        traceback.format_exc(),
                    )
                    raise CookidooParseException(
                        "Loading recipes failed during parsing of request response."
                    ) from e
        except TimeoutError as e:
            _LOGGER.debug(
                "Exception: Cannot get recipes:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Loading recipes failed due to connection timeout."
            ) from e
        except ClientError as e:
            _LOGGER.debug(
                "Exception: Cannot recipes:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Loading recipes failed due to request exception."
            ) from e

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

        try:
            url = self.api_endpoint / INGREDIENT_ITEMS_PATH.format(
                **self._cfg.localization.__dict__
            )
            async with self._session.get(url, headers=self._api_headers) as r:
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
                            "Exception: Cannot get ingredient items: %s",
                            errmsg["error_description"],
                        )
                    raise CookidooAuthException(
                        "Loading ingredient items failed due to authorization failure, "
                        "the authorization token is invalid or expired."
                    )

                r.raise_for_status()

                try:
                    _d = await r.json()
                    return [
                        cookidoo_ingredient_item_from_json(cast(ItemJSON, ingredient))
                        for recipe in [*_d["recipes"], *_d["customerRecipes"]]
                        for ingredient in recipe["recipeIngredientGroups"]
                    ]

                except (JSONDecodeError, KeyError) as e:
                    _LOGGER.debug(
                        "Exception: Cannot get ingredient items:\n%s",
                        traceback.format_exc(),
                    )
                    raise CookidooParseException(
                        "Loading ingredient items failed during parsing of request response."
                    ) from e
        except TimeoutError as e:
            _LOGGER.debug(
                "Exception: Cannot get ingredient items:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Loading ingredient items failed due to connection timeout."
            ) from e
        except ClientError as e:
            _LOGGER.debug(
                "Exception: Cannot ingredient items:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Loading ingredient items failed due to request exception."
            ) from e

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
        try:
            url = self.api_endpoint / ADD_INGREDIENT_ITEMS_FOR_RECIPES_PATH.format(
                **self._cfg.localization.__dict__
            )
            async with self._session.post(
                url, headers=self._api_headers, json=json_data
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
                            "Exception: Cannot add ingredient items for recipes: %s",
                            errmsg["error_description"],
                        )
                    raise CookidooAuthException(
                        "Add ingredient items for recipes failed due to authorization failure, "
                        "the authorization token is invalid or expired."
                    )

                r.raise_for_status()
                try:
                    return [
                        cookidoo_ingredient_item_from_json(cast(ItemJSON, ingredient))
                        for recipe in (await r.json())["data"]
                        for ingredient in recipe["recipeIngredientGroups"]
                    ]
                except (JSONDecodeError, KeyError) as e:
                    _LOGGER.debug(
                        "Exception: Cannot get added ingredient items:\n%s",
                        traceback.format_exc(),
                    )
                    raise CookidooParseException(
                        "Loading added ingredient items failed during parsing of request response."
                    ) from e
        except TimeoutError as e:
            _LOGGER.debug(
                "Exception: Cannot execute add ingredient items for recipes:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Add ingredient items for recipes failed due to connection timeout."
            ) from e
        except ClientError as e:
            _LOGGER.debug(
                "Exception: Cannot execute add ingredient items for recipes:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Add ingredient items for recipes failed due to request exception."
            ) from e

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
        try:
            url = self.api_endpoint / REMOVE_INGREDIENT_ITEMS_FOR_RECIPES_PATH.format(
                **self._cfg.localization.__dict__
            )
            async with self._session.post(
                url, headers=self._api_headers, json=json_data
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
                            "Exception: Cannot remove ingredient items for recipes: %s",
                            errmsg["error_description"],
                        )
                    raise CookidooAuthException(
                        "Remove ingredient items for recipes failed due to authorization failure, "
                        "the authorization token is invalid or expired."
                    )

                r.raise_for_status()
        except TimeoutError as e:
            _LOGGER.debug(
                "Exception: Cannot execute remove ingredient items for recipes:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Remove ingredient items for recipes failed due to connection timeout."
            ) from e
        except ClientError as e:
            _LOGGER.debug(
                "Exception: Cannot execute remove ingredient items for recipes:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Remove ingredient items for recipes failed due to request exception."
            ) from e

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
        try:
            url = self.api_endpoint / EDIT_OWNERSHIP_INGREDIENT_ITEMS_PATH.format(
                **self._cfg.localization.__dict__
            )
            async with self._session.post(
                url, headers=self._api_headers, json=json_data
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
                            "Exception: Cannot edit recipe ingredient items ownership: %s",
                            errmsg["error_description"],
                        )
                    raise CookidooAuthException(
                        "Edit ingredient items ownership failed due to authorization failure, "
                        "the authorization token is invalid or expired."
                    )

                r.raise_for_status()
                try:
                    return [
                        cookidoo_ingredient_item_from_json(cast(ItemJSON, ingredient))
                        for ingredient in (await r.json())["data"]
                    ]

                except (JSONDecodeError, KeyError) as e:
                    _LOGGER.debug(
                        "Exception: Cannot get edited ingredient items:\n%s",
                        traceback.format_exc(),
                    )
                    raise CookidooParseException(
                        "Loading edited ingredient items failed during parsing of request response."
                    ) from e
        except TimeoutError as e:
            _LOGGER.debug(
                "Exception: Cannot execute edit ingredient items ownership:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Edit ingredient items ownership failed due to connection timeout."
            ) from e
        except ClientError as e:
            _LOGGER.debug(
                "Exception: Cannot execute edit ingredient items ownership:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Edit ingredient items ownership failed due to request exception."
            ) from e

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
        try:
            url = self.api_endpoint / ADD_INGREDIENT_ITEMS_FOR_RECIPES_PATH.format(
                **self._cfg.localization.__dict__
            )
            async with self._session.post(
                url, headers=self._api_headers, json=json_data
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
                            "Exception: Cannot add ingredient items for custom recipes: %s",
                            errmsg["error_description"],
                        )
                    raise CookidooAuthException(
                        "Add ingredient items for custom recipes failed due to authorization failure, "
                        "the authorization token is invalid or expired."
                    )

                r.raise_for_status()
                try:
                    return [
                        cookidoo_ingredient_item_from_json(cast(ItemJSON, ingredient))
                        for recipe in (await r.json())["data"]
                        for ingredient in recipe["recipeIngredientGroups"]
                    ]
                except (JSONDecodeError, KeyError) as e:
                    _LOGGER.debug(
                        "Exception: Cannot get added ingredient items:\n%s",
                        traceback.format_exc(),
                    )
                    raise CookidooParseException(
                        "Loading added ingredient items failed during parsing of request response."
                    ) from e
        except TimeoutError as e:
            _LOGGER.debug(
                "Exception: Cannot execute add ingredient items for custom recipes:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Add ingredient items for custom recipes failed due to connection timeout."
            ) from e
        except ClientError as e:
            _LOGGER.debug(
                "Exception: Cannot execute add ingredient items for custom recipes:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Add ingredient items for custom recipes failed due to request exception."
            ) from e

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
        try:
            url = self.api_endpoint / REMOVE_INGREDIENT_ITEMS_FOR_RECIPES_PATH.format(
                **self._cfg.localization.__dict__
            )
            async with self._session.post(
                url, headers=self._api_headers, json=json_data
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
                            "Exception: Cannot remove ingredient items for custom recipes: %s",
                            errmsg["error_description"],
                        )
                    raise CookidooAuthException(
                        "Remove ingredient items for custom recipes failed due to authorization failure, "
                        "the authorization token is invalid or expired."
                    )

                r.raise_for_status()
        except TimeoutError as e:
            _LOGGER.debug(
                "Exception: Cannot execute remove ingredient items for custom recipes:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Remove ingredient items for custom recipes failed due to connection timeout."
            ) from e
        except ClientError as e:
            _LOGGER.debug(
                "Exception: Cannot execute remove ingredient items for custom recipes:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Remove ingredient items for custom recipes failed due to request exception."
            ) from e

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

        try:
            url = self.api_endpoint / ADDITIONAL_ITEMS_PATH.format(
                **self._cfg.localization.__dict__
            )
            async with self._session.get(url, headers=self._api_headers) as r:
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
                            "Exception: Cannot get additional items: %s",
                            errmsg["error_description"],
                        )
                    raise CookidooAuthException(
                        "Loading additional items failed due to authorization failure, "
                        "the authorization token is invalid or expired."
                    )

                r.raise_for_status()

                try:
                    return [
                        cookidoo_additional_item_from_json(
                            cast(AdditionalItemJSON, additional_item)
                        )
                        for additional_item in (await r.json())["additionalItems"]
                    ]

                except (JSONDecodeError, KeyError) as e:
                    _LOGGER.debug(
                        "Exception: Cannot get additional items:\n%s",
                        traceback.format_exc(),
                    )
                    raise CookidooParseException(
                        "Loading additional items failed during parsing of request response."
                    ) from e
        except TimeoutError as e:
            _LOGGER.debug(
                "Exception: Cannot get additional items:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Loading additional items failed due to connection timeout."
            ) from e
        except ClientError as e:
            _LOGGER.debug(
                "Exception: Cannot additional items:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Loading additional items failed due to request exception."
            ) from e

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
        try:
            url = self.api_endpoint / ADD_ADDITIONAL_ITEMS_PATH.format(
                **self._cfg.localization.__dict__
            )
            async with self._session.post(
                url, headers=self._api_headers, json=json_data
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
                            "Exception: Cannot add additional items: %s",
                            errmsg["error_description"],
                        )
                    raise CookidooAuthException(
                        "Add additional items failed due to authorization failure, "
                        "the authorization token is invalid or expired."
                    )

                r.raise_for_status()
                try:
                    return [
                        cookidoo_additional_item_from_json(
                            cast(AdditionalItemJSON, additional_item)
                        )
                        for additional_item in (await r.json())["data"]
                    ]

                except (JSONDecodeError, KeyError) as e:
                    _LOGGER.debug(
                        "Exception: Cannot get added additional items:\n%s",
                        traceback.format_exc(),
                    )
                    raise CookidooParseException(
                        "Loading added additional items failed during parsing of request response."
                    ) from e
        except TimeoutError as e:
            _LOGGER.debug(
                "Exception: Cannot execute add additional items:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Add additional items failed due to connection timeout."
            ) from e
        except ClientError as e:
            _LOGGER.debug(
                "Exception: Cannot execute add additional items:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Add additional items failed due to request exception."
            ) from e

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
        try:
            url = self.api_endpoint / EDIT_ADDITIONAL_ITEMS_PATH.format(
                **self._cfg.localization.__dict__
            )
            async with self._session.post(
                url, headers=self._api_headers, json=json_data
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
                            "Exception: Cannot edit additional items: %s",
                            errmsg["error_description"],
                        )
                    raise CookidooAuthException(
                        "Edit additional items failed due to authorization failure, "
                        "the authorization token is invalid or expired."
                    )

                r.raise_for_status()
                try:
                    return [
                        cookidoo_additional_item_from_json(
                            cast(AdditionalItemJSON, additional_item)
                        )
                        for additional_item in (await r.json())["data"]
                    ]

                except (JSONDecodeError, KeyError) as e:
                    _LOGGER.debug(
                        "Exception: Cannot get edited additional items:\n%s",
                        traceback.format_exc(),
                    )
                    raise CookidooParseException(
                        "Loading edited additional items failed during parsing of request response."
                    ) from e
        except TimeoutError as e:
            _LOGGER.debug(
                "Exception: Cannot execute edit additional items:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Edit additional items failed due to connection timeout."
            ) from e
        except ClientError as e:
            _LOGGER.debug(
                "Exception: Cannot execute edit additional items:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Edit additional items failed due to request exception."
            ) from e

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
        try:
            url = self.api_endpoint / EDIT_OWNERSHIP_ADDITIONAL_ITEMS_PATH.format(
                **self._cfg.localization.__dict__
            )
            async with self._session.post(
                url, headers=self._api_headers, json=json_data
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
                            "Exception: Cannot edit additional items ownership: %s",
                            errmsg["error_description"],
                        )
                    raise CookidooAuthException(
                        "Edit additional items ownership failed due to authorization failure, "
                        "the authorization token is invalid or expired."
                    )

                r.raise_for_status()
                try:
                    return [
                        cookidoo_additional_item_from_json(
                            cast(AdditionalItemJSON, additional_item)
                        )
                        for additional_item in (await r.json())["data"]
                    ]

                except (JSONDecodeError, KeyError) as e:
                    _LOGGER.debug(
                        "Exception: Cannot get edited additional items:\n%s",
                        traceback.format_exc(),
                    )
                    raise CookidooParseException(
                        "Loading edited additional items failed during parsing of request response."
                    ) from e
        except TimeoutError as e:
            _LOGGER.debug(
                "Exception: Cannot execute edit additional items ownership:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Edit additional items ownership failed due to connection timeout."
            ) from e
        except ClientError as e:
            _LOGGER.debug(
                "Exception: Cannot execute edit additional items ownership:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Edit additional items ownership failed due to request exception."
            ) from e

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
        try:
            url = self.api_endpoint / REMOVE_ADDITIONAL_ITEMS_PATH.format(
                **self._cfg.localization.__dict__
            )
            async with self._session.post(
                url, headers=self._api_headers, json=json_data
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
                            "Exception: Cannot remove additional items: %s",
                            errmsg["error_description"],
                        )
                    raise CookidooAuthException(
                        "Remove additional items failed due to authorization failure, "
                        "the authorization token is invalid or expired."
                    )

                r.raise_for_status()
        except TimeoutError as e:
            _LOGGER.debug(
                "Exception: Cannot execute remove additional items:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Remove additional items failed due to connection timeout."
            ) from e
        except ClientError as e:
            _LOGGER.debug(
                "Exception: Cannot execute remove additional items:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Remove additional items failed due to request exception."
            ) from e

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
        try:
            url = self.api_endpoint / INGREDIENT_ITEMS_PATH.format(
                **self._cfg.localization.__dict__
            )
            async with self._session.delete(url, headers=self._api_headers) as r:
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
                            "Exception: Cannot clear shopping list: %s",
                            errmsg["error_description"],
                        )
                    raise CookidooAuthException(
                        "Clear shopping list failed due to authorization failure, "
                        "the authorization token is invalid or expired."
                    )

                r.raise_for_status()
        except TimeoutError as e:
            _LOGGER.debug(
                "Exception: Cannot execute clear shopping list:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Clear shopping list failed due to connection timeout."
            ) from e
        except ClientError as e:
            _LOGGER.debug(
                "Exception: Cannot execute clear shopping list:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Clear shopping list failed due to request exception."
            ) from e

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

        try:
            url = self.api_endpoint / MANAGED_COLLECTIONS_PATH.format(
                **self._cfg.localization.__dict__
            )
            async with self._session.get(
                url,
                headers={
                    **self._api_headers,
                    "ACCEPT": MANAGED_COLLECTIONS_PATH_ACCEPT,
                },
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
                            "Exception: Cannot count managed collections: %s",
                            errmsg["error_description"],
                        )
                    raise CookidooAuthException(
                        "Loading managed collections failed due to authorization failure, "
                        "the authorization token is invalid or expired."
                    )

                r.raise_for_status()

                try:
                    json = await r.json()
                    return (
                        int(json["page"]["totalElements"]),
                        int(json["page"]["totalPages"]),
                    )

                except (JSONDecodeError, KeyError) as e:
                    _LOGGER.debug(
                        "Exception: Cannot count managed collections%s",
                        traceback.format_exc(),
                    )
                    raise CookidooParseException(
                        "Loading managed collections during parsing of request response."
                    ) from e
        except TimeoutError as e:
            _LOGGER.debug(
                "Exception: Cannot count managed collections:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Loading managed collections due to connection timeout."
            ) from e
        except ClientError as e:
            _LOGGER.debug(
                "Exception: Cannot count managed collections%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Loading managed collections due to request exception."
            ) from e

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

        try:
            url = self.api_endpoint / MANAGED_COLLECTIONS_PATH.format(
                **self._cfg.localization.__dict__
            )
            async with self._session.get(
                url,
                headers={
                    **self._api_headers,
                    "ACCEPT": MANAGED_COLLECTIONS_PATH_ACCEPT,
                },
                params={"page": page},
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
                            "Exception: Cannot get managed collections: %s",
                            errmsg["error_description"],
                        )
                    raise CookidooAuthException(
                        "Loading managed collections failed due to authorization failure, "
                        "the authorization token is invalid or expired."
                    )

                r.raise_for_status()

                try:
                    return [
                        cookidoo_collection_from_json(cast(ManagedCollectionJSON, list))
                        for list in (await r.json())["managedlists"]
                    ]

                except (JSONDecodeError, KeyError) as e:
                    _LOGGER.debug(
                        "Exception: Cannot get managed collections%s",
                        traceback.format_exc(),
                    )
                    raise CookidooParseException(
                        "Loading managed collections during parsing of request response."
                    ) from e
        except TimeoutError as e:
            _LOGGER.debug(
                "Exception: Cannot get managed collections:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Loading managed collections due to connection timeout."
            ) from e
        except ClientError as e:
            _LOGGER.debug(
                "Exception: Cannot get managed collections%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Loading managed collections due to request exception."
            ) from e

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
        try:
            url = self.api_endpoint / ADD_MANAGED_COLLECTION_PATH.format(
                **self._cfg.localization.__dict__
            )
            async with self._session.post(
                url,
                headers={
                    **self._api_headers,
                    "ACCEPT": MANAGED_COLLECTIONS_PATH_ACCEPT,
                },
                json=json_data,
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
                            "Exception: Cannot add managed collection: %s",
                            errmsg["error_description"],
                        )
                    raise CookidooAuthException(
                        "Add managed collection failed due to authorization failure, "
                        "the authorization token is invalid or expired."
                    )

                r.raise_for_status()
                try:
                    return cookidoo_collection_from_json(
                        cast(ManagedCollectionJSON, (await r.json())["content"])
                    )

                except (JSONDecodeError, KeyError) as e:
                    _LOGGER.debug(
                        "Exception: Cannot get added managed collection:\n%s",
                        traceback.format_exc(),
                    )
                    raise CookidooParseException(
                        "Loading added managed collection failed during parsing of request response."
                    ) from e
        except TimeoutError as e:
            _LOGGER.debug(
                "Exception: Cannot execute add managed collection:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Add managed collection failed due to connection timeout."
            ) from e
        except ClientError as e:
            _LOGGER.debug(
                "Exception: Cannot execute add managed collection:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Add managed collection failed due to request exception."
            ) from e

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
        try:
            url = self.api_endpoint / REMOVE_MANAGED_COLLECTION_PATH.format(
                **self._cfg.localization.__dict__, id=managed_collection_id
            )
            async with self._session.delete(
                url,
                headers={
                    **self._api_headers,
                    "ACCEPT": MANAGED_COLLECTIONS_PATH_ACCEPT,
                },
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
                            "Exception: Cannot remove managed collection: %s",
                            errmsg["error_description"],
                        )
                    raise CookidooAuthException(
                        "Remove managed collection failed due to authorization failure, "
                        "the authorization token is invalid or expired."
                    )

                r.raise_for_status()
        except TimeoutError as e:
            _LOGGER.debug(
                "Exception: Cannot execute remove managed collection:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Remove managed collection failed due to connection timeout."
            ) from e
        except ClientError as e:
            _LOGGER.debug(
                "Exception: Cannot execute remove managed collection:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Remove managed collection failed due to request exception."
            ) from e

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

        try:
            url = self.api_endpoint / CUSTOM_COLLECTIONS_PATH.format(
                **self._cfg.localization.__dict__
            )
            async with self._session.get(
                url,
                headers={
                    **self._api_headers,
                    "ACCEPT": CUSTOM_COLLECTIONS_PATH_ACCEPT,
                },
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
                            "Exception: Cannot count custom collections: %s",
                            errmsg["error_description"],
                        )
                    raise CookidooAuthException(
                        "Loading custom collections failed due to authorization failure, "
                        "the authorization token is invalid or expired."
                    )

                r.raise_for_status()

                try:
                    json = await r.json()
                    return (
                        int(json["page"]["totalElements"]),
                        int(json["page"]["totalPages"]),
                    )

                except (JSONDecodeError, KeyError) as e:
                    _LOGGER.debug(
                        "Exception: Cannot count custom collections%s",
                        traceback.format_exc(),
                    )
                    raise CookidooParseException(
                        "Loading custom collections during parsing of request response."
                    ) from e
        except TimeoutError as e:
            _LOGGER.debug(
                "Exception: Cannot count custom collections:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Loading custom collections due to connection timeout."
            ) from e
        except ClientError as e:
            _LOGGER.debug(
                "Exception: Cannot count custom collections%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Loading custom collections due to request exception."
            ) from e

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

        try:
            url = self.api_endpoint / CUSTOM_COLLECTIONS_PATH.format(
                **self._cfg.localization.__dict__
            )
            async with self._session.get(
                url,
                headers={
                    **self._api_headers,
                    "ACCEPT": CUSTOM_COLLECTIONS_PATH_ACCEPT,
                },
                params={"page": page},
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
                            "Exception: Cannot get custom collections: %s",
                            errmsg["error_description"],
                        )
                    raise CookidooAuthException(
                        "Loading custom collections failed due to authorization failure, "
                        "the authorization token is invalid or expired."
                    )

                r.raise_for_status()

                try:
                    return [
                        cookidoo_collection_from_json(cast(CustomCollectionJSON, list))
                        for list in (await r.json())["customlists"]
                    ]

                except (JSONDecodeError, KeyError) as e:
                    _LOGGER.debug(
                        "Exception: Cannot get custom collections%s",
                        traceback.format_exc(),
                    )
                    raise CookidooParseException(
                        "Loading custom collections during parsing of request response."
                    ) from e
        except TimeoutError as e:
            _LOGGER.debug(
                "Exception: Cannot get custom collections:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Loading custom collections due to connection timeout."
            ) from e
        except ClientError as e:
            _LOGGER.debug(
                "Exception: Cannot get custom collections%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Loading custom collections due to request exception."
            ) from e

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
        try:
            url = self.api_endpoint / ADD_CUSTOM_COLLECTION_PATH.format(
                **self._cfg.localization.__dict__
            )
            async with self._session.post(
                url,
                headers={
                    **self._api_headers,
                    "ACCEPT": CUSTOM_COLLECTIONS_PATH_ACCEPT,
                },
                json=json_data,
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
                            "Exception: Cannot add custom collection: %s",
                            errmsg["error_description"],
                        )
                    raise CookidooAuthException(
                        "Add custom collection failed due to authorization failure, "
                        "the authorization token is invalid or expired."
                    )

                r.raise_for_status()
                try:
                    return cookidoo_collection_from_json(
                        cast(CustomCollectionJSON, (await r.json())["content"])
                    )

                except (JSONDecodeError, KeyError) as e:
                    _LOGGER.debug(
                        "Exception: Cannot get added custom collection:\n%s",
                        traceback.format_exc(),
                    )
                    raise CookidooParseException(
                        "Loading added custom collection failed during parsing of request response."
                    ) from e
        except TimeoutError as e:
            _LOGGER.debug(
                "Exception: Cannot execute add custom collection:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Add custom collection failed due to connection timeout."
            ) from e
        except ClientError as e:
            _LOGGER.debug(
                "Exception: Cannot execute add custom collection:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Add custom collection failed due to request exception."
            ) from e

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
        try:
            url = self.api_endpoint / REMOVE_CUSTOM_COLLECTION_PATH.format(
                **self._cfg.localization.__dict__, id=custom_collection_id
            )
            async with self._session.delete(
                url,
                headers={
                    **self._api_headers,
                    "ACCEPT": CUSTOM_COLLECTIONS_PATH_ACCEPT,
                },
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
                            "Exception: Cannot remove custom collection: %s",
                            errmsg["error_description"],
                        )
                    raise CookidooAuthException(
                        "Remove custom collection failed due to authorization failure, "
                        "the authorization token is invalid or expired."
                    )

                r.raise_for_status()
        except TimeoutError as e:
            _LOGGER.debug(
                "Exception: Cannot execute remove custom collection:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Remove custom collection failed due to connection timeout."
            ) from e
        except ClientError as e:
            _LOGGER.debug(
                "Exception: Cannot execute remove custom collection:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Remove custom collection failed due to request exception."
            ) from e

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
        try:
            url = self.api_endpoint / ADD_RECIPES_TO_CUSTOM_COLLECTION_PATH.format(
                **self._cfg.localization.__dict__, id=custom_collection_id
            )
            async with self._session.put(
                url, headers=self._api_headers, json=json_data
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
                            "Exception: Cannot add recipes to custom collection: %s",
                            errmsg["error_description"],
                        )
                    raise CookidooAuthException(
                        "Add recipes to custom collection failed due to authorization failure, "
                        "the authorization token is invalid or expired."
                    )

                r.raise_for_status()
                try:
                    return cookidoo_collection_from_json(
                        cast(CustomCollectionJSON, (await r.json())["content"])
                    )

                except (JSONDecodeError, KeyError) as e:
                    _LOGGER.debug(
                        "Exception: Cannot get added recipes:\n%s",
                        traceback.format_exc(),
                    )
                    raise CookidooParseException(
                        "Loading added recipes failed during parsing of request response."
                    ) from e
        except TimeoutError as e:
            _LOGGER.debug(
                "Exception: Cannot execute add recipes to custom collection:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Add recipes to custom collection failed due to connection timeout."
            ) from e
        except ClientError as e:
            _LOGGER.debug(
                "Exception: Cannot execute add recipes to custom collection:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Add recipes to custom collection failed due to request exception."
            ) from e

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
        try:
            url = self.api_endpoint / REMOVE_RECIPE_FROM_CUSTOM_COLLECTION_PATH.format(
                **self._cfg.localization.__dict__,
                id=custom_collection_id,
                recipe=recipe_id,
            )
            async with self._session.delete(url, headers=self._api_headers) as r:
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
                            "Exception: Cannot remove recipe from custom collection: %s",
                            errmsg["error_description"],
                        )
                    raise CookidooAuthException(
                        "Remove recipe from custom collection failed due to authorization failure, "
                        "the authorization token is invalid or expired."
                    )

                r.raise_for_status()
                try:
                    return cookidoo_collection_from_json(
                        cast(CustomCollectionJSON, (await r.json())["content"])
                    )

                except (JSONDecodeError, KeyError) as e:
                    _LOGGER.debug(
                        "Exception: Cannot get removed recipe:\n%s",
                        traceback.format_exc(),
                    )
                    raise CookidooParseException(
                        "Loading removed recipe failed during parsing of request response."
                    ) from e
        except TimeoutError as e:
            _LOGGER.debug(
                "Exception: Cannot execute add recipe from custom collection:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Remove recipe from custom collection failed due to connection timeout."
            ) from e
        except ClientError as e:
            _LOGGER.debug(
                "Exception: Cannot execute remove recipe from custom collection:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Remove recipe from custom collection failed due to request exception."
            ) from e

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

        try:
            url = self.api_endpoint / RECIPES_IN_CALENDAR_WEEK_PATH.format(
                **self._cfg.localization.__dict__, day=day.isoformat()
            )
            async with self._session.get(url, headers=self._api_headers) as r:
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
                            "Exception: Cannot get recipes in calendar week: %s",
                            errmsg["error_description"],
                        )
                    raise CookidooAuthException(
                        "Loading recipes in calendar week failed due to authorization failure, "
                        "the authorization token is invalid or expired."
                    )

                r.raise_for_status()

                try:
                    return [
                        cookidoo_calendar_day_from_json(
                            cast(CalendarDayJSON, day), self._cfg.localization
                        )
                        for day in (await r.json())["myDays"]
                    ]

                except (JSONDecodeError, KeyError) as e:
                    _LOGGER.debug(
                        "Exception: Cannot get recipes in calendar day%s",
                        traceback.format_exc(),
                    )
                    raise CookidooParseException(
                        "Loading recipes in calendar day during parsing of request response."
                    ) from e
        except TimeoutError as e:
            _LOGGER.debug(
                "Exception: Cannot get recipes in calendar day:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Loading recipes in calendar day due to connection timeout."
            ) from e
        except ClientError as e:
            _LOGGER.debug(
                "Exception: Cannot get recipes in calendar day%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Loading recipes in calendar day due to request exception."
            ) from e

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
        try:
            url = self.api_endpoint / ADD_RECIPES_TO_CALENDER_PATH.format(
                **self._cfg.localization.__dict__
            )
            async with self._session.put(
                url, headers=self._api_headers, json=json_data
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
                            "Exception: Cannot add recipes to calendar: %s",
                            errmsg["error_description"],
                        )
                    raise CookidooAuthException(
                        "Add recipes to calendar failed due to authorization failure, "
                        "the authorization token is invalid or expired."
                    )

                r.raise_for_status()
                try:
                    return cookidoo_calendar_day_from_json(
                        cast(CalendarDayJSON, (await r.json())["content"]),
                        self._cfg.localization,
                    )

                except (JSONDecodeError, KeyError) as e:
                    _LOGGER.debug(
                        "Exception: Cannot get added recipes:\n%s",
                        traceback.format_exc(),
                    )
                    raise CookidooParseException(
                        "Loading added recipes failed during parsing of request response."
                    ) from e
        except TimeoutError as e:
            _LOGGER.debug(
                "Exception: Cannot execute add recipes to calendar:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Add recipes to calendar failed due to connection timeout."
            ) from e
        except ClientError as e:
            _LOGGER.debug(
                "Exception: Cannot execute add recipes to calendar:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Add recipes to calendar failed due to request exception."
            ) from e

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
        try:
            url = self.api_endpoint / REMOVE_RECIPE_FROM_CALENDER_PATH.format(
                **self._cfg.localization.__dict__,
                day=day.isoformat(),
                recipe=recipe_id,
            )
            async with self._session.delete(url, headers=self._api_headers) as r:
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
                            "Exception: Cannot remove recipe from calendar: %s",
                            errmsg["error_description"],
                        )
                    raise CookidooAuthException(
                        "Remove recipe from calendar failed due to authorization failure, "
                        "the authorization token is invalid or expired."
                    )

                r.raise_for_status()
                try:
                    return cookidoo_calendar_day_from_json(
                        cast(CalendarDayJSON, (await r.json())["content"]),
                        self._cfg.localization,
                    )

                except (JSONDecodeError, KeyError) as e:
                    _LOGGER.debug(
                        "Exception: Cannot get removed recipe:\n%s",
                        traceback.format_exc(),
                    )
                    raise CookidooParseException(
                        "Loading removed recipe failed during parsing of request response."
                    ) from e
        except TimeoutError as e:
            _LOGGER.debug(
                "Exception: Cannot execute remove recipe from calendar:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Remove recipe from calendar failed due to connection timeout."
            ) from e
        except ClientError as e:
            _LOGGER.debug(
                "Exception: Cannot execute remove recipe from calendar:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Remove recipe from calendar failed due to request exception."
            ) from e

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
        try:
            url = self.api_endpoint / ADD_RECIPES_TO_CALENDER_PATH.format(
                **self._cfg.localization.__dict__
            )
            async with self._session.put(
                url, headers=self._api_headers, json=json_data
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
                            "Exception: Cannot add custom recipes to calendar: %s",
                            errmsg["error_description"],
                        )
                    raise CookidooAuthException(
                        "Add custom recipes to calendar failed due to authorization failure, "
                        "the authorization token is invalid or expired."
                    )

                r.raise_for_status()
                try:
                    return cookidoo_calendar_day_from_json(
                        cast(CalendarDayJSON, (await r.json())["content"]),
                        self._cfg.localization,
                    )

                except (JSONDecodeError, KeyError) as e:
                    _LOGGER.debug(
                        "Exception: Cannot get added custom recipes:\n%s",
                        traceback.format_exc(),
                    )
                    raise CookidooParseException(
                        "Loading added custom recipes failed during parsing of request response."
                    ) from e
        except TimeoutError as e:
            _LOGGER.debug(
                "Exception: Cannot execute add custom recipes to calendar:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Add custom recipes to calendar failed due to connection timeout."
            ) from e
        except ClientError as e:
            _LOGGER.debug(
                "Exception: Cannot execute add custom recipes to calendar:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Add custom recipes to calendar failed due to request exception."
            ) from e

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
        try:
            url = self.api_endpoint / REMOVE_RECIPE_FROM_CALENDER_PATH.format(
                **self._cfg.localization.__dict__,
                day=day.isoformat(),
                recipe=recipe_id,
            )
            async with self._session.delete(
                url, headers=self._api_headers, params={"recipeSource": "CUSTOMER"}
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
                            "Exception: Cannot remove custom recipe from calendar: %s",
                            errmsg["error_description"],
                        )
                    raise CookidooAuthException(
                        "Remove custom recipe from calendar failed due to authorization failure, "
                        "the authorization token is invalid or expired."
                    )

                r.raise_for_status()
                try:
                    return cookidoo_calendar_day_from_json(
                        cast(CalendarDayJSON, (await r.json())["content"]),
                        self._cfg.localization,
                    )

                except (JSONDecodeError, KeyError) as e:
                    _LOGGER.debug(
                        "Exception: Cannot get custom removed recipe:\n%s",
                        traceback.format_exc(),
                    )
                    raise CookidooParseException(
                        "Loading custom removed recipe failed during parsing of request response."
                    ) from e
        except TimeoutError as e:
            _LOGGER.debug(
                "Exception: Cannot execute remove custom recipe from calendar:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Remove custom recipe from calendar failed due to connection timeout."
            ) from e
        except ClientError as e:
            _LOGGER.debug(
                "Exception: Cannot execute remove custom recipe from calendar:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Remove custom recipe from calendar failed due to request exception."
            ) from e
