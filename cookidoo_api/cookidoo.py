"""Cookidoo api implementation."""

from datetime import date
from http import HTTPStatus
from json import JSONDecodeError
import logging
import time
import traceback
from typing import cast

from aiohttp import ClientError, ClientSession, FormData
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
    API_ENDPOINT,
    AUTHORIZATION_HEADER,
    CO_UK_COUNTRY_CODE,
    COMMUNITY_PROFILE_PATH,
    COOKIDOO_CLIENT_ID,
    CUSTOM_COLLECTIONS_PATH,
    CUSTOM_COLLECTIONS_PATH_ACCEPT,
    CUSTOM_RECIPE_PATH,
    DEFAULT_API_HEADERS,
    DEFAULT_TOKEN_HEADERS,
    EDIT_ADDITIONAL_ITEMS_PATH,
    EDIT_OWNERSHIP_ADDITIONAL_ITEMS_PATH,
    EDIT_OWNERSHIP_INGREDIENT_ITEMS_PATH,
    INGREDIENT_ITEMS_PATH,
    INTERNATIONAL_COUNTRY_CODE,
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
    TOKEN_PATH,
)
from cookidoo_api.exceptions import (
    CookidooAuthException,
    CookidooConfigException,
    CookidooParseException,
    CookidooRequestException,
)
from cookidoo_api.helpers import (
    cookidoo_additional_item_from_json,
    cookidoo_auth_data_from_json,
    cookidoo_calendar_day_from_json,
    cookidoo_collection_from_json,
    cookidoo_custom_recipe_from_json,
    cookidoo_ingredient_item_from_json,
    cookidoo_recipe_details_from_json,
    cookidoo_recipe_from_json,
    cookidoo_subscription_from_json,
    cookidoo_user_info_from_json,
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
    CookidooAuthResponse,
    CookidooCalendarDay,
    CookidooCollection,
    CookidooConfig,
    CookidooCustomRecipe,
    CookidooIngredientItem,
    CookidooLocalizationConfig,
    CookidooShoppingRecipe,
    CookidooShoppingRecipeDetails,
    CookidooSubscription,
    CookidooUserInfo,
)

_LOGGER = logging.getLogger(__name__)


class Cookidoo:
    """Unofficial Cookidoo API interface."""

    _session: ClientSession
    _cfg: CookidooConfig
    _token_headers: dict[str, str]
    _api_headers: dict[str, str]
    _auth_data: CookidooAuthResponse | None

    def __init__(
        self,
        session: ClientSession,
        cfg: CookidooConfig = CookidooConfig(),
    ) -> None:
        """Init function for Bring API.

        Parameters
        ----------
        session
            The client session for aiohttp requests
        cfg
            Cookidoo config


        """
        self._session = session
        self._cfg = cfg
        self._token_headers = DEFAULT_TOKEN_HEADERS.copy()
        self._api_headers = DEFAULT_API_HEADERS.copy()
        self.__expires_in: int
        self._auth_data = None

    @property
    def localization(self) -> CookidooLocalizationConfig:
        """Localization."""
        return self._cfg.localization

    @property
    def expires_in(self) -> int:
        """Refresh token expiration."""
        return max(0, self.__expires_in - int(time.time()))

    @expires_in.setter
    def expires_in(self, expires_in: int | str) -> None:
        self.__expires_in = int(time.time()) + int(expires_in)

    @property
    def auth_data(self) -> CookidooAuthResponse | None:
        """Auth data."""
        return self._auth_data if self._auth_data else None

    @auth_data.setter
    def auth_data(self, auth_data: CookidooAuthResponse) -> None:
        self._api_headers["AUTHORIZATION"] = AUTHORIZATION_HEADER.format(
            type=auth_data.token_type.lower().capitalize(),
            access_token=auth_data.access_token,
        )
        self._auth_data = auth_data
        self.expires_in = auth_data.expires_in

    @property
    def api_endpoint(self) -> URL:
        """Get the api endpoint."""
        if "international" in self._cfg.localization.url:
            return URL(API_ENDPOINT.format(country_code=INTERNATIONAL_COUNTRY_CODE))
        if "co.uk" in self._cfg.localization.url:
            return URL(API_ENDPOINT.format(country_code=CO_UK_COUNTRY_CODE))
        return URL(API_ENDPOINT.format(**self._cfg.localization.__dict__))

    async def refresh_token(self) -> CookidooAuthResponse:
        """Try to refresh the token.

        Returns
        -------
        CookidooAuthResponse
            The auth response object.

        Raises
        ------
        CookidooConfigException
            If no login has happened yet
        CookidooRequestException
            If the request fails.
        CookidooParseException
            If the parsing of the request response fails.
        CookidooAuthException
            If the login fails due invalid credentials.
            You should check your email and password.

        """
        if not self._auth_data:
            raise CookidooConfigException("No auth data available, please log in first")

        refresh_data = FormData()
        refresh_data.add_field("grant_type", "refresh_token")
        refresh_data.add_field("refresh_token", self._auth_data.refresh_token)
        refresh_data.add_field("client_id", COOKIDOO_CLIENT_ID)

        return await self._request_access_token(refresh_data)

    async def login(self) -> CookidooAuthResponse:
        """Try to login.

        Returns
        -------
        CookidooAuthResponse
            The auth response object.

        Raises
        ------
        CookidooRequestException
            If the request fails.
        CookidooParseException
            If the parsing of the request response fails.
        CookidooAuthException
            If the login fails due invalid credentials.
            You should check your email and password.

        """
        user_data = FormData()
        user_data.add_field("grant_type", "password")
        user_data.add_field("username", self._cfg.email)
        user_data.add_field("password", self._cfg.password)

        return await self._request_access_token(user_data)

    async def _request_access_token(self, form_data: FormData) -> CookidooAuthResponse:
        """Request a new access token.

        Parameters
        ----------
        form_data
            The data to be passed to the request with user credentials or refresh token

        Returns
        -------
        CookidooAuthResponse
            The auth response object.

        Raises
        ------
        CookidooRequestException
            If the request fails.
        CookidooParseException
            If the parsing of the request response fails.
        CookidooAuthException
            If the access token request fails due invalid credentials.
            You should check your email and password or refresh token.

        """

        try:
            url = self.api_endpoint / TOKEN_PATH.format(
                **self._cfg.localization.__dict__
            )
            async with self._session.post(
                url, data=form_data, headers=self._token_headers
            ) as r:
                _LOGGER.debug(
                    "Response from %s [%s]: %s",
                    url,
                    r.status,
                    await r.text()
                    if r.status != 200
                    else "",  # do not log response on success, as it contains sensible data
                )

                if r.status == HTTPStatus.UNAUTHORIZED:
                    try:
                        errmsg = await r.json()
                    except (JSONDecodeError, ClientError):
                        _LOGGER.debug(
                            "Exception: Cannot parse access token request response:\n %s",
                            traceback.format_exc(),
                        )
                    else:
                        _LOGGER.debug(
                            "Exception: Cannot request access token: %s",
                            errmsg["error_description"],
                        )
                    raise CookidooAuthException(
                        "Access token request failed due to authorization failure, "
                        "please check your email and password or refresh token."
                    )
                if r.status == HTTPStatus.BAD_REQUEST:
                    _LOGGER.debug(
                        "Exception: Cannot request access token: %s", await r.text()
                    )
                    raise CookidooAuthException(
                        "Access token request failed due to bad request, please check your email or refresh token."
                    )
                r.raise_for_status()

                try:
                    data = cookidoo_auth_data_from_json(await r.json())
                except JSONDecodeError as e:
                    _LOGGER.debug(
                        "Exception: Cannot request access token:\n %s",
                        traceback.format_exc(),
                    )
                    raise CookidooParseException(
                        "Cannot parse access token request response."
                    ) from e
        except TimeoutError as e:
            _LOGGER.debug(
                "Exception: Cannot request access token:\n %s", traceback.format_exc()
            )
            raise CookidooRequestException(
                "Authentication failed due to connection timeout."
            ) from e
        except ClientError as e:
            _LOGGER.debug(
                "Exception: Cannot request access token:\n %s", traceback.format_exc()
            )
            raise CookidooRequestException(
                "Authentication failed due to request exception."
            ) from e

        self.auth_data = data

        return data

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
                    return cookidoo_user_info_from_json((await r.json())["userInfo"])
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
