"""Cookidoo api implementation."""

import asyncio
import base64
from collections.abc import Callable, Mapping, Sequence
from datetime import date
import hashlib
from http import HTTPStatus
import json
from json import JSONDecodeError
import logging
import os
from pathlib import Path
import re
import secrets
import time
import traceback
from typing import TypeVar, cast
from urllib.parse import parse_qs, urljoin, urlparse

from aiohttp import ClientError, ClientSession
from yarl import URL

from cookidoo_api.const import (
    CIAM_BASE_URL,
    CIAM_LOGIN_SRV_URL,
    CUSTOM_COLLECTIONS_PATH_ACCEPT,
    CUSTOM_RECIPES_PATH_ACCEPT,
    DEFAULT_API_HEADERS,
    HAL_ACCEPT,
    LOGIN_HEADERS,
    MANAGED_COLLECTIONS_PATH_ACCEPT,
    MOBILE_HOME_PATH,
    OAUTH_SCOPE,
    OIDC_DISCOVERY_URL,
    PUSH_BUNDLE_ID,
    PUSH_PLATFORM,
    REL_RMI_CONFIG,
    RMI_API_VERSION,
    RMI_DEVICES,
    RMI_REGISTER_TOKEN,
    RMI_UNREGISTER,
    TOKEN_EXPIRY_MARGIN_S,
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
    cookidoo_device_from_json,
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
    CustomRecipesJSON,
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
    CookidooAuthData,
    CookidooCalendarDay,
    CookidooCollection,
    CookidooConfig,
    CookidooCustomRecipe,
    CookidooDevice,
    CookidooIngredientItem,
    CookidooLocalizationConfig,
    CookidooSearchResult,
    CookidooShoppingRecipe,
    CookidooShoppingRecipeDetails,
    CookidooSubscription,
    CookidooUserInfo,
    ThermomixMachineType,
)
from cookidoo_api.well_known import resolve_endpoint_paths

_LOGGER = logging.getLogger(__name__)
_T = TypeVar("_T")


class Cookidoo:
    """Unofficial Cookidoo API interface."""

    _session: ClientSession
    _cfg: CookidooConfig
    _api_headers: dict[str, str]
    _logged_in: bool
    _endpoint_overrides: dict[str, str]
    _endpoints_resolved: bool
    _endpoints_lock: asyncio.Lock
    _refresh_token: str | None
    _expires_at: float
    _oidc: dict[str, str] | None
    _rmi_links: dict[str, str] | None

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
        self._endpoint_overrides = {}
        self._endpoints_resolved = False
        self._endpoints_lock = asyncio.Lock()
        self._refresh_token = None
        self._expires_at = 0.0
        self._oidc = None
        self._rmi_links = None

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
        await self._ensure_token()
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

    def _is_endpoints_resolved(self) -> bool:
        """Return whether endpoint discovery has already completed.

        Kept as a method (rather than a direct attribute read) so mypy
        doesn't narrow ``_endpoints_resolved`` to a stale literal across the
        ``await`` on ``_endpoints_lock`` in ``_ensure_endpoints``.
        """
        return self._endpoints_resolved

    async def _ensure_endpoints(self) -> None:
        """Resolve live endpoint paths via ``.well-known/home`` discovery.

        Runs once per instance. There is no hardcoded fallback: a stale
        path is worse than a clear failure, since it can look successful
        right up until Cookidoo actually removes the old one. Discovery is
        retried once (a transient network hiccup shouldn't need a whole new
        request cycle to recover from); if the retry also fails, the
        exception propagates to the caller and the next call starts over
        from scratch.

        Guarded by a lock (checked both before and inside it) so concurrent
        callers -- e.g. an ``asyncio.gather`` of several API methods on a
        fresh instance -- await a single in-flight resolution instead of
        each kicking off their own full discovery round.

        Raises
        ------
        CookidooRequestException
            If a service's discovery document could not be reached.
        CookidooParseException
            If a discovered endpoint's shape can't be reconciled with ours.

        """
        if self._endpoints_resolved:
            return
        async with self._endpoints_lock:
            # Re-check via a helper: a direct attribute re-check here is
            # (correctly) flagged as unreachable by mypy, since it can't
            # know the `await` above (waiting on the lock) may let another
            # coroutine change `_endpoints_resolved` in the meantime.
            if self._is_endpoints_resolved():
                return
            try:
                self._endpoint_overrides = await resolve_endpoint_paths(
                    self._session, self.api_endpoint
                )
            except (CookidooRequestException, CookidooParseException):
                _LOGGER.debug(
                    "Well-known endpoint discovery failed, retrying once:\n%s",
                    traceback.format_exc(),
                )
                self._endpoint_overrides = await resolve_endpoint_paths(
                    self._session, self.api_endpoint
                )
            self._endpoints_resolved = True

    def _path(self, name: str) -> str:
        """Return the live path template resolved via well-known discovery."""
        return self._endpoint_overrides[name]

    @staticmethod
    def _empty_calendar_day(day: date) -> CookidooCalendarDay:
        """Build an empty calendar day for a day with no recipes left.

        The API returns a null ``content`` when a recipe removal leaves a
        calendar day with no recipes, since the (now empty) day no longer
        exists as an entity to return.
        """
        return CookidooCalendarDay(
            id=day.isoformat(),
            title=day.isoformat(),
            recipes=[],
        )

    @property
    def auth_data(self) -> CookidooAuthData | None:
        """The current OAuth2 tokens, for persistence. ``None`` until logged in."""
        if not self._logged_in or self._refresh_token is None:
            return None
        return CookidooAuthData(
            access_token=self._api_headers["Authorization"].removeprefix("Bearer "),
            refresh_token=self._refresh_token,
            expires_at=self._expires_at,
        )

    def apply_auth_data(self, auth_data: CookidooAuthData) -> None:
        """Restore a previous login from persisted tokens (no network call).

        The access token is refreshed automatically on the next request if it
        has expired.
        """
        self._api_headers["Authorization"] = f"Bearer {auth_data.access_token}"
        self._refresh_token = auth_data.refresh_token
        self._expires_at = auth_data.expires_at
        self._logged_in = True

    async def login(self) -> None:
        """Perform an OAuth2 authorization-code + PKCE login.

        Signs in with the configured email/password against the CIAM identity
        provider, exchanges the resulting code for an access/refresh token, and
        authenticates all subsequent API calls via a ``Bearer`` header:

        1. discover the OIDC endpoints
        2. open the authorize endpoint to reach the CIAM login form
        3. POST the credentials to the CIAM login service
        4. capture the ``code`` from the redirect to the app scheme
        5. exchange the code for tokens (public client, PKCE, no secret)

        The login redirects still rely on the session cookie jar, so a
        ``CookieJar(unsafe=True)`` session is required. The login requests carry
        a browser-like ``User-Agent`` (request-scoped only) since the flow is
        served behind Cloudflare.

        Raises
        ------
        CookidooConfigException
            If the OAuth2 client id or redirect uri was overridden with an
            empty value.
        CookidooRequestException
            If the request fails.
        CookidooParseException
            If the login page cannot be parsed.
        CookidooAuthException
            If the login fails due to invalid credentials.

        """
        self._assert_oauth_client()
        try:
            oidc = await self._discovery()
            verifier, challenge = self._pkce_pair()
            state = secrets.token_urlsafe(12)
            language = self._cfg.localization.language
            params = {
                "response_type": "code",
                "client_id": self._cfg.client_id,
                "redirect_uri": self._cfg.redirect_uri,
                "market": self._cfg.localization.country_code,
                "scope": OAUTH_SCOPE,
                "state": state,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "ui_locales": language,
            }

            # Step 2: reach the CIAM login form (follows redirects, sets cookies)
            async with self._session.get(
                URL(oidc["authorization_endpoint"]),
                params=params,
                allow_redirects=True,
                headers=LOGIN_HEADERS,
            ) as resp:
                self._check_login_page_status(resp.status)
                login_html = await resp.text()

            # Step 3: submit credentials, Step 4: capture the authorization code
            request_id = self._extract_request_id(login_html)
            code = await self._submit_credentials(request_id, state)

            # Step 5: exchange the code for tokens
            await self._exchange_code(oidc["token_endpoint"], code, verifier)
            self._logged_in = True

        except (CookidooAuthException, CookidooParseException):
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

    async def refresh(self) -> None:
        """Refresh the access token using the stored refresh token.

        Raises
        ------
        CookidooAuthException
            If there is no refresh token or the refresh is rejected.
        CookidooConfigException
            If the OAuth2 client id or redirect uri was overridden with an
            empty value.
        CookidooRequestException
            If the request fails.

        """
        if self._refresh_token is None:
            raise CookidooAuthException("Cannot refresh: no refresh token available.")
        self._assert_oauth_client()
        oidc = await self._discovery()
        try:
            async with self._session.post(
                URL(oidc["token_endpoint"]),
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self._refresh_token,
                    "client_id": self._cfg.client_id,
                },
                headers=LOGIN_HEADERS,
            ) as resp:
                if resp.status != HTTPStatus.OK:
                    raise CookidooAuthException(
                        f"Token refresh failed (status {resp.status})."
                    )
                payload = cast(dict[str, object], await resp.json())
        except ClientError as e:
            raise CookidooRequestException(
                "Token refresh failed due to request exception."
            ) from e
        self._apply_tokens(payload)

    def save_token(self, path: str | Path) -> None:
        """Save the OAuth2 tokens to a file for later reuse.

        Parameters
        ----------
        path
            Path to the file where the tokens will be saved.

        """
        if (auth_data := self.auth_data) is None:
            raise CookidooConfigException("Cannot save token: not logged in.")
        Path(path).write_text(json.dumps(vars(auth_data)), encoding="utf-8")

    def load_token(self, path: str | Path) -> None:
        """Restore the OAuth2 tokens from a file saved with :meth:`save_token`.

        Parameters
        ----------
        path
            Path to the file containing the saved tokens.

        Raises
        ------
        CookidooConfigException
            If the token file cannot be read or parsed.

        """
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            self.apply_auth_data(CookidooAuthData(**data))
        except (OSError, json.JSONDecodeError, TypeError) as e:
            raise CookidooConfigException(f"Cannot load token from {path}.") from e

    # -- internal auth helpers --------------------------------------------
    async def _discovery(self) -> dict[str, str]:
        """Fetch and cache the OIDC discovery document."""
        if self._oidc is None:
            async with self._session.get(
                URL(OIDC_DISCOVERY_URL), headers=LOGIN_HEADERS
            ) as resp:
                resp.raise_for_status()
                self._oidc = cast(dict[str, str], await resp.json())
        return self._oidc

    async def _submit_credentials(self, request_id: str, state: str) -> str:
        """POST credentials and follow the redirect chain to capture the code.

        Raises ``CookidooAuthException`` when no authorization code is returned
        (i.e. the credentials were rejected).
        """
        url: str = CIAM_LOGIN_SRV_URL
        data: dict[str, str] | None = {
            "requestId": request_id,
            "username": self._cfg.email,
            "password": self._cfg.password,
        }
        method = "post"
        code: str | None = None
        for _ in range(10):
            async with self._session.request(
                method,
                URL(url),
                data=data,
                headers=LOGIN_HEADERS,
                allow_redirects=False,
            ) as resp:
                location = resp.headers.get("Location")
                if resp.status in (301, 302, 303, 307, 308) and location:
                    if location.startswith(self._cfg.redirect_uri):
                        query = parse_qs(urlparse(location).query)
                        # A missing state is a mismatch: the callback must echo
                        # the value we sent (RFC 6749 §10.12).
                        if query.get("state") != [state]:
                            raise CookidooAuthException("OAuth state mismatch.")
                        codes = query.get("code")
                        code = codes[0] if codes else None
                        break
                    url = urljoin(url, location)
                    self._assert_ciam_origin(url)
                    method, data = "get", None
                    continue
                break
        if code is None:
            raise CookidooAuthException(
                "Login failed: invalid credentials (no authorization code "
                "returned). Please check your email and password."
            )
        return code

    @staticmethod
    def _assert_ciam_origin(url: str) -> None:
        """Ensure the login flow never leaves CIAM's own origin.

        The redirect chain carries the session cookies of an in-flight login, so
        a redirect to a foreign host is refused rather than followed.
        """
        origin = urlparse(url)
        expected = urlparse(CIAM_BASE_URL)
        if (origin.scheme, origin.netloc) != (expected.scheme, expected.netloc):
            raise CookidooAuthException(
                f"Login flow redirected off the authentication host: {url}"
            )

    @staticmethod
    def _check_login_page_status(status: int) -> None:
        """Check login page response status."""
        if status != HTTPStatus.OK:
            raise CookidooAuthException(
                f"Login flow failed: could not reach login page (status {status})."
            )

    async def _exchange_code(
        self, token_endpoint: str, code: str, verifier: str
    ) -> None:
        """Exchange an authorization code for tokens."""
        async with self._session.post(
            URL(token_endpoint),
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self._cfg.redirect_uri,
                "code_verifier": verifier,
                "client_id": self._cfg.client_id,
            },
            headers=LOGIN_HEADERS,
        ) as resp:
            if resp.status != HTTPStatus.OK:
                raise CookidooAuthException(
                    f"Token exchange failed (status {resp.status})."
                )
            payload = cast(dict[str, object], await resp.json())
        self._apply_tokens(payload)

    def _apply_tokens(self, payload: dict[str, object]) -> None:
        """Store tokens from a token-endpoint response and set the auth header."""
        try:
            access_token = cast(str, payload["access_token"])
            # A refresh response may omit a new refresh token; keep the old one.
            self._refresh_token = cast(
                str, payload.get("refresh_token", self._refresh_token)
            )
            expires_in = int(cast(int, payload.get("expires_in", 43200)))
        except (KeyError, TypeError, ValueError) as e:
            raise CookidooAuthException(f"Unexpected token response: {payload}") from e
        self._api_headers["Authorization"] = f"Bearer {access_token}"
        self._expires_at = time.time() + expires_in

    async def _ensure_token(self) -> None:
        """Refresh the access token if it is missing or about to expire."""
        if not self._logged_in:
            return
        if time.time() >= self._expires_at - TOKEN_EXPIRY_MARGIN_S:
            await self.refresh()

    @staticmethod
    def _pkce_pair() -> tuple[str, str]:
        """Return a (code_verifier, code_challenge) PKCE S256 pair."""
        verifier = base64.urlsafe_b64encode(os.urandom(48)).rstrip(b"=").decode()
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
            .rstrip(b"=")
            .decode()
        )
        return verifier, challenge

    def _assert_oauth_client(self) -> None:
        """Ensure the OAuth2 client identifiers are set.

        Both default to the mobile app's public identifiers, so this only trips
        when a caller overrides one of them with an empty value.

        Raises
        ------
        CookidooConfigException
            If the client id or the redirect uri is missing.

        """
        missing = [
            name
            for name in ("client_id", "redirect_uri")
            if not getattr(self._cfg, name)
        ]
        if missing:
            raise CookidooConfigException(
                f"Missing OAuth2 client configuration: {', '.join(missing)}. "
                "Leave these unset to use the defaults, see docs/oauth-client.md."
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

        await self._ensure_endpoints()
        url = self.api_endpoint / self._path(
            "community-profile:user-private-profile"
        ).format(**self._cfg.localization.__dict__)
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

        await self._ensure_endpoints()
        url = self.api_endpoint / self._path("ownership:subscriptions").format(
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

    async def get_devices(self) -> list[CookidooDevice]:
        """Get the Thermomix appliances paired to the account.

        Returns
        -------
        list[CookidooDevice]
            The paired appliances, identified by machine type (e.g. ``TM7``).
            An empty list when no appliance is paired.

        Raises
        ------
        CookidooAuthException
            When the access token is not valid anymore
        CookidooRequestException
            If the request fails.
        CookidooParseException
            If the parsing of the request response fails.

        """
        await self._ensure_endpoints()
        url = self.api_endpoint / self._path(
            "customer-devices:thermomix-versions"
        ).format(**self._cfg.localization.__dict__)
        result = await self._request_json("get", url, "loading devices")
        if result is None:
            # An account without a paired appliance gets a 204 No Content.
            return []
        models = self._ensure_sequence(result, "loading devices")
        return self._parse_result(
            "loading devices",
            lambda: [cookidoo_device_from_json(cast(str, model)) for model in models],
        )

    async def _resolve_rmi_links(self) -> dict[str, str]:
        """Resolve and cache the remote-monitoring endpoint links.

        Walks the mobile home document to the ``rmi-config`` sub-document and
        returns its ``{rel: href}`` map (``rmi:register-token``, ``rmi:devices``,
        ``rmi:unregister``, ...).
        """
        if self._rmi_links is not None:
            return self._rmi_links

        hal_headers = {"ACCEPT": HAL_ACCEPT}
        home = self._ensure_mapping(
            await self._request_json(
                "get",
                self.api_endpoint / MOBILE_HOME_PATH,
                "resolving remote monitoring",
                headers=hal_headers,
            ),
            "resolving remote monitoring",
        )
        rmi_config_url = self._hal_link(home, REL_RMI_CONFIG)
        if rmi_config_url is None:
            raise CookidooParseException(
                "Resolving remote monitoring failed: rmi-config link missing."
            )
        rmi_home = self._ensure_mapping(
            await self._request_json(
                "get",
                URL(rmi_config_url),
                "resolving remote monitoring",
                headers=hal_headers,
            ),
            "resolving remote monitoring",
        )
        links_obj = rmi_home.get("_links")
        if not isinstance(links_obj, Mapping):
            raise CookidooParseException(
                "Resolving remote monitoring failed during parsing of request response."
            )
        links: dict[str, str] = {}
        for rel, value in links_obj.items():
            if isinstance(value, str):
                links[rel] = value
            elif isinstance(value, Mapping) and isinstance(value.get("href"), str):
                links[rel] = cast(str, value["href"])
        self._rmi_links = links
        return links

    @staticmethod
    def _hal_link(doc: Mapping[str, object], rel: str) -> str | None:
        """Extract a HAL link href for ``rel`` from a document's ``_links``."""
        links = doc.get("_links")
        if not isinstance(links, Mapping):
            return None
        value = links.get(rel)
        if isinstance(value, str):
            return value
        if isinstance(value, Mapping) and isinstance(value.get("href"), str):
            return cast(str, value["href"])
        return None

    async def get_monitored_device_ids(self) -> list[str]:
        """Get the appliance IDs currently available for remote monitoring.

        Note this is distinct from :meth:`get_devices` (all paired appliances):
        an appliance only appears here while it is online/reachable for
        monitoring, and the identifier is the opaque remote-monitoring device id.

        Returns
        -------
        list[str]
            The remote-monitoring device ids (empty when none are available).

        Raises
        ------
        CookidooAuthException
            When the access token is not valid anymore
        CookidooRequestException
            If the request fails.
        CookidooParseException
            If the parsing of the request response fails.

        """
        links = await self._resolve_rmi_links()
        url = links.get(RMI_DEVICES)
        if url is None:
            raise CookidooParseException("rmi:devices link missing.")
        devices = self._ensure_sequence(
            await self._request_json(
                "get", URL(url.split("{")[0]), "loading monitored devices"
            ),
            "loading monitored devices",
        )
        return self._parse_result(
            "loading monitored devices",
            lambda: [
                cast(str, cast(Mapping[str, object], device)["deviceId"])
                for device in devices
            ],
        )

    async def register_push_token(self, push_token: str, mobile_app_id: str) -> None:
        """Register a push token to receive remote-monitoring cook-state updates.

        Appliance state is delivered as a Firebase Cloud Messaging data message
        to the registered token; obtaining the token and receiving the messages
        is the caller's responsibility. Decode received payloads with
        :func:`cookidoo_api.cooking_activity_from_push`.

        Parameters
        ----------
        push_token
            The FCM registration token to deliver updates to.
        mobile_app_id
            A stable per-installation identifier for this client.

        Raises
        ------
        CookidooAuthException
            When the access token is not valid anymore
        CookidooRequestException
            If the request fails.
        CookidooParseException
            If the parsing of the request response fails.

        """
        links = await self._resolve_rmi_links()
        url = links.get(RMI_REGISTER_TOKEN)
        if url is None:
            raise CookidooParseException("rmi:register-token link missing.")
        await self._request_json(
            "post",
            URL(url),
            "registering push token",
            json={
                "token": push_token,
                "bundleId": PUSH_BUNDLE_ID,
                "platform": PUSH_PLATFORM,
                "mobileAppId": mobile_app_id,
            },
            headers={"rmi-api-version": RMI_API_VERSION},
            parse_response=False,
        )

    async def unregister_push_token(self, push_token: str) -> None:
        """Unregister a previously registered push token.

        Parameters
        ----------
        push_token
            The FCM registration token to stop delivering updates to.

        Raises
        ------
        CookidooAuthException
            When the access token is not valid anymore
        CookidooRequestException
            If the request fails.
        CookidooParseException
            If the parsing of the request response fails.

        """
        links = await self._resolve_rmi_links()
        url = links.get(RMI_UNREGISTER)
        if url is None:
            raise CookidooParseException("rmi:unregister link missing.")
        await self._request_json(
            "delete",
            URL(url),
            "unregistering push token",
            json={"tokens": [push_token]},
            headers={"rmi-api-version": RMI_API_VERSION},
            parse_response=False,
        )

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

        await self._ensure_endpoints()
        url = self.api_endpoint / self._path("recipe:details").format(
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
        *,
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
        await self._ensure_endpoints()
        url = self.api_endpoint / self._path("search:home").format(locale=locale)
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

        await self._ensure_endpoints()
        url = self.api_endpoint / self._path("customer-recipes:recipe-details").format(
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

    async def list_custom_recipes(self) -> list[CookidooCustomRecipe]:
        """List custom recipes."""
        await self._ensure_endpoints()
        url = self.api_endpoint / self._path("customer-recipes:recipe-create").format(
            **self._cfg.localization.__dict__
        )
        result = self._ensure_mapping(
            await self._request_json(
                "get",
                url,
                "listing custom recipes",
                headers={"ACCEPT": CUSTOM_RECIPES_PATH_ACCEPT},
            ),
            "listing custom recipes",
        )
        if not isinstance(result.get("items"), list):
            raise CookidooParseException(
                "Listing custom recipes failed during parsing of request response."
            )

        custom_recipes = cast(CustomRecipesJSON, result)
        return self._parse_result(
            "listing custom recipes",
            lambda: [
                cookidoo_custom_recipe_from_json(recipe, self._cfg.localization)
                for recipe in custom_recipes["items"]
            ],
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
        await self._ensure_endpoints()
        json_data = {
            "recipeUrl": str(
                self.api_endpoint
                / self._path("recipe:details").format(
                    **self._cfg.localization.__dict__, id=recipeId
                )
            ),
            "servingSize": servingSize,
        }
        url = self.api_endpoint / self._path("customer-recipes:recipe-create").format(
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
        await self._ensure_endpoints()
        url = self.api_endpoint / self._path("customer-recipes:recipe-details").format(
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

        await self._ensure_endpoints()
        url = self.api_endpoint / self._path("pantry:home").format(
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

        await self._ensure_endpoints()
        url = self.api_endpoint / self._path("pantry:home").format(
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
        await self._ensure_endpoints()
        url = self.api_endpoint / self._path("pantry:recipe-ingredients").format(
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
        await self._ensure_endpoints()
        url = self.api_endpoint / self._path("pantry:remove-recipe").format(
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
        await self._ensure_endpoints()
        url = self.api_endpoint / self._path(
            "pantry:edit-ingredients-ownership"
        ).format(**self._cfg.localization.__dict__)
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
        await self._ensure_endpoints()
        url = self.api_endpoint / self._path("pantry:recipe-ingredients").format(
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
        await self._ensure_endpoints()
        url = self.api_endpoint / self._path("pantry:remove-recipe").format(
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

        await self._ensure_endpoints()
        url = self.api_endpoint / self._path("pantry:home").format(
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
        await self._ensure_endpoints()
        url = self.api_endpoint / self._path("pantry:add-additional-items-v2").format(
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
        await self._ensure_endpoints()
        url = self.api_endpoint / self._path("pantry:edit-additional-items").format(
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
        await self._ensure_endpoints()
        url = self.api_endpoint / self._path(
            "pantry:edit-additional-items-ownership"
        ).format(**self._cfg.localization.__dict__)
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
        await self._ensure_endpoints()
        url = self.api_endpoint / self._path("pantry:remove-additional-items").format(
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
        await self._ensure_endpoints()
        url = self.api_endpoint / self._path("pantry:home").format(
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

        await self._ensure_endpoints()
        url = self.api_endpoint / self._path("organize:api-managed-list").format(
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

        await self._ensure_endpoints()
        url = self.api_endpoint / self._path("organize:api-managed-list").format(
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
        await self._ensure_endpoints()
        url = self.api_endpoint / self._path("organize:api-managed-list").format(
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
        await self._ensure_endpoints()
        url = self.api_endpoint / self._path("organize:api-managed-list-single").format(
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

        await self._ensure_endpoints()
        url = self.api_endpoint / self._path("organize:api-custom-list").format(
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

        await self._ensure_endpoints()
        url = self.api_endpoint / self._path("organize:api-custom-list").format(
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
        await self._ensure_endpoints()
        url = self.api_endpoint / self._path("organize:api-custom-list").format(
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
        await self._ensure_endpoints()
        url = self.api_endpoint / self._path("organize:api-custom-list-modify").format(
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
        await self._ensure_endpoints()
        url = self.api_endpoint / self._path("organize:api-custom-list-modify").format(
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
        await self._ensure_endpoints()
        url = self.api_endpoint / self._path("organize:api-custom-list-recipe").format(
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

        await self._ensure_endpoints()
        url = self.api_endpoint / self._path("planning:api-my-week-from-date").format(
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
        await self._ensure_endpoints()
        url = self.api_endpoint / self._path("planning:api-my-day").format(
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
        await self._ensure_endpoints()
        url = self.api_endpoint / self._path("planning:api-my-day-recipes").format(
            **self._cfg.localization.__dict__,
            day=day.isoformat(),
            recipe=recipe_id,
        )
        result = self._ensure_mapping(
            await self._request_json("delete", url, "remove recipe from calendar"),
            "remove recipe from calendar",
        )
        if result.get("content") is None:
            # The API returns a null content when the removed recipe was the
            # last one for the day, since the (now empty) day no longer
            # exists as an entity.
            return self._empty_calendar_day(day)
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
        await self._ensure_endpoints()
        url = self.api_endpoint / self._path("planning:api-my-day").format(
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
        await self._ensure_endpoints()
        url = self.api_endpoint / self._path("planning:api-my-day-recipes").format(
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
        if result.get("content") is None:
            # The API returns a null content when the removed recipe was the
            # last one for the day, since the (now empty) day no longer
            # exists as an entity.
            return self._empty_calendar_day(day)
        return self._parse_result(
            "loading custom removed recipe",
            lambda: cookidoo_calendar_day_from_json(
                cast(CalendarDayJSON, result["content"]),
                self._cfg.localization,
            ),
        )
