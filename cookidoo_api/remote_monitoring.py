"""Live appliance cook state over Firebase Cloud Messaging.

The remote-monitoring backend has no endpoint that returns the current cook
state: an appliance pushes its state to the Cookidoo mobile app as a Firebase
Cloud Messaging *data message*. To observe it, a client has to register a push
token of its own (:meth:`Cookidoo.register_push_token`) and then receive those
messages.

:class:`CookidooRemoteMonitoring` does both. It obtains an FCM registration
token without an Android device (via ``firebase-messaging``), registers it,
and decodes every incoming message with
:func:`cookidoo_api.cooking_activity_from_push` before handing it to a callback.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import json
import logging
from typing import Any

from aiohttp import ClientSession
from firebase_messaging import FcmPushClient, FcmRegisterConfig

from cookidoo_api.const import (
    FCM_API_KEY,
    FCM_APP_ID,
    FCM_PROJECT_ID,
    FCM_SENDER_ID,
    PUSH_NESTED_PAYLOAD_KEYS,
)
from cookidoo_api.cookidoo import Cookidoo
from cookidoo_api.helpers import cooking_activity_from_push
from cookidoo_api.types import CookidooCookingActivity

_LOGGER = logging.getLogger(__name__)


def cook_state_payload(message: Any) -> dict[str, Any] | None:
    """Extract the cook-state mapping from a Firebase data message.

    The appliance flattens the cook fields into the data map, but the app's push
    service also accepts them nested under ``cookingActivity`` /
    ``remoteMonitoringInfo`` (as an object or as a JSON string), so all three
    shapes are accepted here.

    Returns
    -------
    dict[str, Any] | None
        The cook-state mapping, or ``None`` if the message carries none.

    """
    if not isinstance(message, dict):
        return None
    data = message.get("data", message)
    if not isinstance(data, dict):
        return None
    if "deviceId" in data:
        return data
    return _nested_cook_state(data)


def _nested_cook_state(data: dict[str, Any]) -> dict[str, Any] | None:
    """Return the cook state nested under one of the known payload keys."""
    for key in PUSH_NESTED_PAYLOAD_KEYS:
        value = data.get(key)
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                return dict(json.loads(value))
            except (json.JSONDecodeError, TypeError, ValueError):
                _LOGGER.debug("Could not decode the %s push payload", key)
                return None
    return None


def token_from_credentials(credentials: Any) -> str | None:
    """Return the FCM registration token held by a credentials mapping.

    Returns
    -------
    str | None
        The token, or ``None`` if the mapping does not carry one.

    """
    try:
        token = credentials["fcm"]["registration"]["token"]
    except (KeyError, TypeError):
        return None
    return token if isinstance(token, str) else None


class CookidooRemoteMonitoring:
    """Receives live cook state for the appliances of an account.

    The FCM credentials are worth persisting: reusing them keeps the same push
    token across restarts instead of leaving a new one registered every time.
    Pass them back in via ``credentials`` and keep them fresh with
    ``on_credentials``.
    """

    def __init__(
        self,
        cookidoo: Cookidoo,
        on_cooking_activity: Callable[[CookidooCookingActivity], None],
        *,
        mobile_app_id: str,
        session: ClientSession | None = None,
        credentials: dict[str, Any] | None = None,
        on_credentials: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        """Init the remote monitoring receiver.

        Parameters
        ----------
        cookidoo
            A logged-in client, used to register and unregister the push token.
        on_cooking_activity
            Called with every decoded cook-state update. Invoked from the event
            loop the receiver runs on.
        mobile_app_id
            A stable per-installation identifier for this client.
        session
            Client session for the Firebase requests. A private one is created
            when omitted.
        credentials
            FCM credentials from a previous run, to reuse its push token.
        on_credentials
            Called whenever the FCM credentials change, for persistence.

        """
        self._cookidoo = cookidoo
        self._on_cooking_activity = on_cooking_activity
        self._mobile_app_id = mobile_app_id
        self._session = session
        self._credentials = credentials
        self._on_credentials = on_credentials
        self._client: FcmPushClient | None = None
        self._token: str | None = None
        self._registered_token: str | None = None
        self._reregister_task: asyncio.Task[None] | None = None

    @property
    def credentials(self) -> dict[str, Any] | None:
        """The current FCM credentials, for persistence."""
        return self._credentials

    @property
    def token(self) -> str | None:
        """The current FCM registration token. ``None`` until started."""
        return self._token

    async def start(self) -> None:
        """Start listening and register for cook-state pushes.

        Raises
        ------
        CookidooAuthException
            When the access token is not valid anymore
        CookidooRequestException
            If registering the push token fails.
        CookidooParseException
            If the remote-monitoring endpoints cannot be resolved.

        """
        self._client = FcmPushClient(
            self._handle_message,
            FcmRegisterConfig(
                project_id=FCM_PROJECT_ID,
                app_id=FCM_APP_ID,
                api_key=FCM_API_KEY,
                messaging_sender_id=FCM_SENDER_ID,
            ),
            self._credentials,
            self._handle_credentials,
            http_client_session=self._session,
        )
        self._token = await self._client.checkin_or_register()
        await self._client.start()
        await self._register(self._token)

    async def stop(self) -> None:
        """Stop listening and drop the push token registration."""
        if self._reregister_task is not None:
            self._reregister_task.cancel()
            self._reregister_task = None
        if self._registered_token is not None:
            try:
                await self._cookidoo.unregister_push_token(self._registered_token)
            except Exception:
                _LOGGER.debug("Unregistering the push token failed", exc_info=True)
            self._registered_token = None
        if self._client is not None:
            await self._client.stop()
            self._client = None

    async def _register(self, token: str) -> None:
        """Subscribe ``token`` to this account's appliance state."""
        await self._cookidoo.register_push_token(token, self._mobile_app_id)
        self._registered_token = token

    def _handle_message(
        self, message: dict[str, Any], persistent_id: str, context: Any = None
    ) -> None:
        """Decode a push message and report the cook state it carries."""
        payload = cook_state_payload(message)
        if payload is None:
            _LOGGER.debug("Ignoring a push without cook state: %s", sorted(message))
            return
        self._on_cooking_activity(cooking_activity_from_push(payload))

    def _handle_credentials(self, credentials: dict[str, Any]) -> None:
        """Persist rotated FCM credentials and re-register a rotated token."""
        self._credentials = credentials
        if self._on_credentials is not None:
            self._on_credentials(credentials)
        # A rotated token receives nothing until it is registered in its turn.
        token = token_from_credentials(credentials)
        if token is not None and token != self._registered_token:
            self._token = token
            self._reregister_task = asyncio.create_task(self._async_reregister(token))

    async def _async_reregister(self, token: str) -> None:
        """Re-register after a token rotation, without killing the receiver."""
        try:
            await self._register(token)
        except Exception:
            _LOGGER.warning("Re-registering the rotated push token failed")
            _LOGGER.debug("Re-registration traceback", exc_info=True)
