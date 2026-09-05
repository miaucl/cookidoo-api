"""Unit tests for the remote-monitoring push receiver."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cookidoo_api.cookidoo import Cookidoo
from cookidoo_api.remote_monitoring import (
    CookidooRemoteMonitoring,
    cook_state_payload,
    token_from_credentials,
)
from cookidoo_api.types import CookidooCookingActivity, CookidooCookState

from .responses import COOKIDOO_TEST_PUSH_COOKING_ACTIVITY

MOBILE_APP_ID = "c4805c69-0000-0000-0000-000000000000"
TOKEN = "fcm-token"
ROTATED_TOKEN = "fcm-token-rotated"


def credentials(token: str) -> dict[str, Any]:
    """Build an FCM credentials mapping carrying ``token``."""
    return {"fcm": {"registration": {"token": token}}}


@pytest.fixture(name="push_client")
def mock_push_client() -> Any:
    """Patch FcmPushClient with a mock that reports a registration token."""
    with patch(
        "cookidoo_api.remote_monitoring.FcmPushClient", autospec=True
    ) as mock_client:
        client = mock_client.return_value
        client.checkin_or_register.return_value = TOKEN
        yield mock_client


class TestCookStatePayload:
    """Tests for extracting the cook state out of a push message."""

    @pytest.mark.parametrize(
        "message",
        [
            pytest.param(COOKIDOO_TEST_PUSH_COOKING_ACTIVITY, id="flattened"),
            pytest.param(
                {"data": COOKIDOO_TEST_PUSH_COOKING_ACTIVITY}, id="under-data"
            ),
            pytest.param(
                {"data": {"cookingActivity": COOKIDOO_TEST_PUSH_COOKING_ACTIVITY}},
                id="nested-object",
            ),
            pytest.param(
                {
                    "data": {
                        "remoteMonitoringInfo": json.dumps(
                            COOKIDOO_TEST_PUSH_COOKING_ACTIVITY
                        )
                    }
                },
                id="nested-json-string",
            ),
        ],
    )
    def test_accepted_shapes(self, message: Any) -> None:
        """Every shape the app's push service accepts yields the cook state."""
        assert cook_state_payload(message) == COOKIDOO_TEST_PUSH_COOKING_ACTIVITY

    @pytest.mark.parametrize(
        "message",
        [
            pytest.param("not-a-mapping", id="not-a-dict"),
            pytest.param({"data": "not-a-mapping"}, id="data-not-a-dict"),
            pytest.param({"data": {"unrelated": "message"}}, id="no-cook-state"),
            pytest.param(
                {"data": {"cookingActivity": "{not json"}}, id="undecodable-json"
            ),
        ],
    )
    def test_rejected_shapes(self, message: Any) -> None:
        """A message without a usable cook state yields ``None``."""
        assert cook_state_payload(message) is None


@pytest.mark.parametrize(
    ("creds", "expected"),
    [
        pytest.param(credentials(TOKEN), TOKEN, id="present"),
        pytest.param({"fcm": {}}, None, id="incomplete"),
        pytest.param({"fcm": {"registration": {"token": 42}}}, None, id="not-a-string"),
        pytest.param(None, None, id="missing"),
    ],
)
def test_token_from_credentials(creds: Any, expected: str | None) -> None:
    """The registration token is read defensively out of the credentials."""
    assert token_from_credentials(creds) == expected


class TestRemoteMonitoring:
    """Tests for the receiver lifecycle."""

    async def test_start_registers_the_token(
        self, cookidoo: Cookidoo, push_client: MagicMock
    ) -> None:
        """Starting checks in with Firebase and subscribes the token."""
        cookidoo.register_push_token = AsyncMock()  # type: ignore[method-assign]
        monitoring = CookidooRemoteMonitoring(
            cookidoo, MagicMock(), mobile_app_id=MOBILE_APP_ID
        )

        await monitoring.start()

        assert monitoring.token == TOKEN
        push_client.return_value.start.assert_awaited_once()
        cookidoo.register_push_token.assert_awaited_once_with(TOKEN, MOBILE_APP_ID)

    async def test_stop_unregisters_the_token(
        self, cookidoo: Cookidoo, push_client: MagicMock
    ) -> None:
        """Stopping drops the subscription and the client."""
        cookidoo.register_push_token = AsyncMock()  # type: ignore[method-assign]
        cookidoo.unregister_push_token = AsyncMock()  # type: ignore[method-assign]
        monitoring = CookidooRemoteMonitoring(
            cookidoo, MagicMock(), mobile_app_id=MOBILE_APP_ID
        )
        await monitoring.start()

        await monitoring.stop()

        cookidoo.unregister_push_token.assert_awaited_once_with(TOKEN)
        push_client.return_value.stop.assert_awaited_once()

    async def test_stop_before_start_is_a_noop(self, cookidoo: Cookidoo) -> None:
        """Stopping a receiver that never started does nothing."""
        cookidoo.unregister_push_token = AsyncMock()  # type: ignore[method-assign]

        await CookidooRemoteMonitoring(
            cookidoo, MagicMock(), mobile_app_id=MOBILE_APP_ID
        ).stop()

        cookidoo.unregister_push_token.assert_not_awaited()

    async def test_stop_survives_a_failing_unregister(
        self, cookidoo: Cookidoo, push_client: MagicMock
    ) -> None:
        """A backend that refuses the unregister still lets the client stop."""
        cookidoo.register_push_token = AsyncMock()  # type: ignore[method-assign]
        cookidoo.unregister_push_token = AsyncMock(  # type: ignore[method-assign]
            side_effect=Exception("nope")
        )
        monitoring = CookidooRemoteMonitoring(
            cookidoo, MagicMock(), mobile_app_id=MOBILE_APP_ID
        )
        await monitoring.start()

        await monitoring.stop()

        push_client.return_value.stop.assert_awaited_once()

    async def test_push_is_decoded_to_a_cooking_activity(
        self, cookidoo: Cookidoo, push_client: MagicMock
    ) -> None:
        """An incoming push reaches the callback as a typed cooking activity."""
        cookidoo.register_push_token = AsyncMock()  # type: ignore[method-assign]
        received: list[CookidooCookingActivity] = []
        monitoring = CookidooRemoteMonitoring(
            cookidoo, received.append, mobile_app_id=MOBILE_APP_ID
        )
        await monitoring.start()

        handler = push_client.call_args.args[0]
        handler(COOKIDOO_TEST_PUSH_COOKING_ACTIVITY, "persistent-id")

        assert len(received) == 1
        assert received[0].state is CookidooCookState.RUNNING
        assert received[0].recipe_name == "Purè di patate"
        assert received[0].target_temperature == 95

    async def test_push_without_cook_state_is_ignored(
        self, cookidoo: Cookidoo, push_client: MagicMock
    ) -> None:
        """A push carrying something else does not reach the callback."""
        cookidoo.register_push_token = AsyncMock()  # type: ignore[method-assign]
        on_activity = MagicMock()
        monitoring = CookidooRemoteMonitoring(
            cookidoo, on_activity, mobile_app_id=MOBILE_APP_ID
        )
        await monitoring.start()

        handler = push_client.call_args.args[0]
        handler({"data": {"unrelated": "message"}}, "persistent-id")

        on_activity.assert_not_called()

    async def test_credentials_are_reported(
        self, cookidoo: Cookidoo, push_client: MagicMock
    ) -> None:
        """Rotated credentials are exposed and handed to the callback."""
        cookidoo.register_push_token = AsyncMock()  # type: ignore[method-assign]
        on_credentials = MagicMock()
        monitoring = CookidooRemoteMonitoring(
            cookidoo,
            MagicMock(),
            mobile_app_id=MOBILE_APP_ID,
            on_credentials=on_credentials,
        )
        await monitoring.start()

        creds = credentials(TOKEN)
        push_client.call_args.args[3](creds)

        assert monitoring.credentials == creds
        on_credentials.assert_called_once_with(creds)
        # The token did not change, so nothing is re-registered.
        cookidoo.register_push_token.assert_awaited_once_with(TOKEN, MOBILE_APP_ID)

    async def test_rotated_token_is_reregistered(
        self, cookidoo: Cookidoo, push_client: MagicMock
    ) -> None:
        """A token rotation resubscribes, or the pushes stop arriving."""
        cookidoo.register_push_token = AsyncMock()  # type: ignore[method-assign]
        monitoring = CookidooRemoteMonitoring(
            cookidoo, MagicMock(), mobile_app_id=MOBILE_APP_ID
        )
        await monitoring.start()

        push_client.call_args.args[3](credentials(ROTATED_TOKEN))
        await asyncio.sleep(0)

        assert monitoring.token == ROTATED_TOKEN
        cookidoo.register_push_token.assert_awaited_with(ROTATED_TOKEN, MOBILE_APP_ID)

    async def test_failed_reregistration_is_swallowed(
        self, cookidoo: Cookidoo, push_client: MagicMock
    ) -> None:
        """A re-registration that fails must not take the receiver down."""
        cookidoo.register_push_token = AsyncMock(  # type: ignore[method-assign]
            side_effect=[None, Exception("nope")]
        )
        monitoring = CookidooRemoteMonitoring(
            cookidoo, MagicMock(), mobile_app_id=MOBILE_APP_ID
        )
        await monitoring.start()

        push_client.call_args.args[3](credentials(ROTATED_TOKEN))
        await asyncio.sleep(0)

        assert monitoring.token == ROTATED_TOKEN

    async def test_stop_cancels_a_pending_reregistration(
        self, cookidoo: Cookidoo, push_client: MagicMock
    ) -> None:
        """Stopping mid-rotation must not leave the re-registration running."""
        blocked = asyncio.Event()

        async def _register(token: str, _mobile_app_id: str) -> None:
            if token == ROTATED_TOKEN:
                await blocked.wait()

        cookidoo.register_push_token = AsyncMock(  # type: ignore[method-assign]
            side_effect=_register
        )
        cookidoo.unregister_push_token = AsyncMock()  # type: ignore[method-assign]
        monitoring = CookidooRemoteMonitoring(
            cookidoo, MagicMock(), mobile_app_id=MOBILE_APP_ID
        )
        await monitoring.start()
        push_client.call_args.args[3](credentials(ROTATED_TOKEN))
        await asyncio.sleep(0)

        await monitoring.stop()

        push_client.return_value.stop.assert_awaited_once()

    async def test_stored_credentials_are_reused(
        self, cookidoo: Cookidoo, push_client: MagicMock
    ) -> None:
        """Credentials from a previous run are handed to the Firebase client."""
        cookidoo.register_push_token = AsyncMock()  # type: ignore[method-assign]
        stored = credentials(TOKEN)

        await CookidooRemoteMonitoring(
            cookidoo, MagicMock(), mobile_app_id=MOBILE_APP_ID, credentials=stored
        ).start()

        assert push_client.call_args.args[2] == stored
