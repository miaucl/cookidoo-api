"""Cookidoo api implementation."""

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
    ADD_INGREDIENTS_FOR_RECIPES_PATH,
    ADDITIONAL_ITEMS_PATH,
    API_ENDPOINT,
    AUTHORIZATION_HEADER,
    COMMUNITY_PROFILE_PATH,
    COOKIDOO_CLIENT_ID,
    DEFAULT_API_HEADERS,
    DEFAULT_COOKIDOO_CONFIG,
    DEFAULT_SITE,
    DEFAULT_TOKEN_HEADERS,
    EDIT_ADDITIONAL_ITEMS_PATH,
    EDIT_OWNERSHIP_ADDITIONAL_ITEMS_PATH,
    EDIT_OWNERSHIP_INGREDIENTS_PATH,
    INGREDIENTS_PATH,
    REMOVE_ADDITIONAL_ITEMS_PATH,
    REMOVE_INGREDIENTS_FOR_RECIPES_PATH,
    SHOPPING_LIST_RECIPES_PATH,
    SUBSCRIPTIONS_PATH,
    TOKEN_ENDPOINT,
)
from cookidoo_api.exceptions import (
    CookidooAuthException,
    CookidooConfigException,
    CookidooParseException,
    CookidooRequestException,
)
from cookidoo_api.helpers import (
    cookidoo_item_from_ingredient,
    cookidoo_recipe_from_json,
)
from cookidoo_api.types import (
    CookidooAuthResponse,
    CookidooConfig,
    CookidooItem,
    CookidooLocalizationConfig,
    CookidooRecipe,
    CookidooSubscription,
    CookidooUserInfo,
    IngredientJSON,
    RecipeJSON,
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
        cfg: CookidooConfig = DEFAULT_COOKIDOO_CONFIG,
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
        return self._cfg["localization"].copy()

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
        return self._auth_data.copy() if self._auth_data else None

    @auth_data.setter
    def auth_data(self, auth_data: CookidooAuthResponse) -> None:
        self._api_headers["AUTHORIZATION"] = AUTHORIZATION_HEADER.format(
            type=auth_data["token_type"].lower().capitalize(),
            access_token=auth_data["access_token"],
        )
        self._auth_data = auth_data
        self.expires_in = auth_data["expires_in"]

    @property
    def api_endpoint(self) -> URL:
        """Get the api endpoint."""
        return URL(API_ENDPOINT.format(**self._cfg["localization"]))

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
        refresh_data.add_field("refresh_token", self._auth_data["refresh_token"])
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
        user_data.add_field("username", self._cfg["email"])
        user_data.add_field("password", self._cfg["password"])

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
            url = TOKEN_ENDPOINT.format(site=DEFAULT_SITE)
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
                    data = cast(
                        CookidooAuthResponse,
                        {
                            key: val
                            for key, val in (await r.json()).items()
                            if key in CookidooAuthResponse.__annotations__
                        },
                    )
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

        return data.copy()

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
                **self._cfg["localization"]
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
                    return cast(
                        CookidooUserInfo,
                        {
                            key: val
                            for key, val in (await r.json())["userInfo"].items()
                            if key in CookidooUserInfo.__annotations__
                        },
                    )

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
                **self._cfg["localization"]
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
                        return cast(
                            CookidooSubscription,
                            {
                                key: val
                                for key, val in subscription.items()
                                if key in CookidooSubscription.__annotations__
                            },
                        )
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

    async def get_shopping_list_recipes(
        self,
    ) -> list[CookidooRecipe]:
        """Get recipes.

        Returns
        -------
        list[CookidooRecipe]
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
                **self._cfg["localization"]
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
                    return [
                        cookidoo_recipe_from_json(cast(RecipeJSON, recipe))
                        for recipe in (await r.json())["recipes"]
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

    async def get_ingredients(
        self,
    ) -> list[CookidooItem]:
        """Get recipe items.

        Returns
        -------
        list[CookidooItem]
            The list of the recipe items

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
            url = self.api_endpoint / INGREDIENTS_PATH.format(
                **self._cfg["localization"]
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
                            "Exception: Cannot get recipe items: %s",
                            errmsg["error_description"],
                        )
                    raise CookidooAuthException(
                        "Loading recipe items failed due to authorization failure, "
                        "the authorization token is invalid or expired."
                    )

                r.raise_for_status()

                try:
                    return [
                        cookidoo_item_from_ingredient(cast(IngredientJSON, ingredient))
                        for recipe in (await r.json())["recipes"]
                        for ingredient in recipe["recipeIngredientGroups"]
                    ]

                except (JSONDecodeError, KeyError) as e:
                    _LOGGER.debug(
                        "Exception: Cannot get recipe items:\n%s",
                        traceback.format_exc(),
                    )
                    raise CookidooParseException(
                        "Loading recipe items failed during parsing of request response."
                    ) from e
        except TimeoutError as e:
            _LOGGER.debug(
                "Exception: Cannot get recipe items:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Loading recipe items failed due to connection timeout."
            ) from e
        except ClientError as e:
            _LOGGER.debug(
                "Exception: Cannot recipe items:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Loading recipe items failed due to request exception."
            ) from e

    async def add_ingredients_for_recipes(
        self,
        recipe_ids: list[str],
    ) -> list[CookidooItem]:
        """Add ingredients for recipes.

        Parameters
        ----------
        recipe_ids
            The recipe ids for the ingredients to add to the shopping list

        Returns
        -------
        list[CookidooItem]
            The list of the added ingredients

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
            url = self.api_endpoint / ADD_INGREDIENTS_FOR_RECIPES_PATH.format(
                **self._cfg["localization"]
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
                            "Exception: Cannot add ingredients for recipes: %s",
                            errmsg["error_description"],
                        )
                    raise CookidooAuthException(
                        "Add ingredients for recipes failed due to authorization failure, "
                        "the authorization token is invalid or expired."
                    )

                r.raise_for_status()
                try:
                    return [
                        cookidoo_item_from_ingredient(cast(IngredientJSON, ingredient))
                        for recipe in (await r.json())["data"]
                        for ingredient in recipe["recipeIngredientGroups"]
                    ]
                except (JSONDecodeError, KeyError) as e:
                    _LOGGER.debug(
                        "Exception: Cannot get added ingredients:\n%s",
                        traceback.format_exc(),
                    )
                    raise CookidooParseException(
                        "Loading added ingredients failed during parsing of request response."
                    ) from e
        except TimeoutError as e:
            _LOGGER.debug(
                "Exception: Cannot execute add ingredients for recipes:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Add ingredients for recipes failed due to connection timeout."
            ) from e
        except ClientError as e:
            _LOGGER.debug(
                "Exception: Cannot execute add ingredients for recipes:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Add ingredients for recipes failed due to request exception."
            ) from e

    async def remove_ingredients_for_recipes(
        self,
        recipe_ids: list[str],
    ) -> None:
        """Remove ingredients for recipes.

        Parameters
        ----------
        recipe_ids
            The recipe ids for the ingredients to remove to the shopping list

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
            url = self.api_endpoint / REMOVE_INGREDIENTS_FOR_RECIPES_PATH.format(
                **self._cfg["localization"]
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
                            "Exception: Cannot remove ingredients for recipes: %s",
                            errmsg["error_description"],
                        )
                    raise CookidooAuthException(
                        "Remove ingredients for recipes failed due to authorization failure, "
                        "the authorization token is invalid or expired."
                    )

                r.raise_for_status()
        except TimeoutError as e:
            _LOGGER.debug(
                "Exception: Cannot execute remove ingredients for recipes:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Remove ingredients for recipes failed due to connection timeout."
            ) from e
        except ClientError as e:
            _LOGGER.debug(
                "Exception: Cannot execute remove ingredients for recipes:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Remove ingredients for recipes failed due to request exception."
            ) from e

    async def edit_ingredients_ownership(
        self,
        ingredients: list[CookidooItem],
    ) -> list[CookidooItem]:
        """Edit ownership recipe items.

        Parameters
        ----------
        ingredients
            The recipe items to change the the `is_owned` value for

        Returns
        -------
        list[CookidooItem]
            The list of the edited recipe items

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
                    "id": ingredient["id"],
                    "isOwned": ingredient["isOwned"],
                    "ownedTimestamp": int(time.time()),
                }
                for ingredient in ingredients
            ]
        }
        try:
            url = self.api_endpoint / EDIT_OWNERSHIP_INGREDIENTS_PATH.format(
                **self._cfg["localization"]
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
                            "Exception: Cannot edit recipe item ownership: %s",
                            errmsg["error_description"],
                        )
                    raise CookidooAuthException(
                        "Edit recipe items ownership failed due to authorization failure, "
                        "the authorization token is invalid or expired."
                    )

                r.raise_for_status()
                try:
                    return [
                        cookidoo_item_from_ingredient(cast(IngredientJSON, ingredient))
                        for ingredient in (await r.json())["data"]
                    ]

                except (JSONDecodeError, KeyError) as e:
                    _LOGGER.debug(
                        "Exception: Cannot get edited recipe items:\n%s",
                        traceback.format_exc(),
                    )
                    raise CookidooParseException(
                        "Loading edited recipe items failed during parsing of request response."
                    ) from e
        except TimeoutError as e:
            _LOGGER.debug(
                "Exception: Cannot execute edit recipe items ownership:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Edit recipe items ownership failed due to connection timeout."
            ) from e
        except ClientError as e:
            _LOGGER.debug(
                "Exception: Cannot execute edit recipe items ownership:\n%s",
                traceback.format_exc(),
            )
            raise CookidooRequestException(
                "Edit recipe items ownership failed due to request exception."
            ) from e

    async def get_additional_items(
        self,
    ) -> list[CookidooItem]:
        """Get additional items.

        Returns
        -------
        list[CookidooItem]
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
                **self._cfg["localization"]
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
                        cast(
                            CookidooItem,
                            {
                                key: val
                                for key, val in additional_item.items()
                                if key in CookidooItem.__annotations__
                            },
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
    ) -> list[CookidooItem]:
        """Create additional items.

        Parameters
        ----------
        additional_item_names
            The additional item names to create, only the label can be set, as the default state `is_owned=false` is forced (chain with immediate update call for work-around)

        Returns
        -------
        list[CookidooItem]
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
                **self._cfg["localization"]
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
                        cast(CookidooItem, additional_item)
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
        additional_items: list[CookidooItem],
    ) -> list[CookidooItem]:
        """Edit additional items.

        Parameters
        ----------
        additional_items
            The additional items to change the the `name` value for

        Returns
        -------
        list[CookidooItem]
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
                    "id": additional_item["id"],
                    "name": additional_item["name"],
                }
                for additional_item in additional_items
            ]
        }
        try:
            url = self.api_endpoint / EDIT_ADDITIONAL_ITEMS_PATH.format(
                **self._cfg["localization"]
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
                        cast(CookidooItem, additional_item)
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
        additional_items: list[CookidooItem],
    ) -> list[CookidooItem]:
        """Edit ownership additional items.

        Parameters
        ----------
        additional_items
            The additional items to change the the `is_owned` value for

        Returns
        -------
        list[CookidooItem]
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
                    "id": additional_item["id"],
                    "isOwned": additional_item["isOwned"],
                    "ownedTimestamp": int(time.time()),
                }
                for additional_item in additional_items
            ]
        }
        try:
            url = self.api_endpoint / EDIT_OWNERSHIP_ADDITIONAL_ITEMS_PATH.format(
                **self._cfg["localization"]
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
                        cast(CookidooItem, additional_item)
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
                **self._cfg["localization"]
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
            url = self.api_endpoint / INGREDIENTS_PATH.format(
                **self._cfg["localization"]
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
