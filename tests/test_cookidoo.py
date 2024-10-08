"""Unit tests for cookidoo-api."""

import socket
from unittest.mock import patch

from dotenv import load_dotenv
import pytest

from cookidoo_api.helpers import (
    cookies_deserialize,
    cookies_serialize,
    error_message_selector,
    merge_cookies,
    resolve_remote_addr,
    timestamped_out_dir,
)
from tests.conftest import TEST_TOKEN_COOKIE

load_dotenv()


class TestCookieSerializing:
    """Test cookie serializing functions."""

    async def test_cookies_deserialize(self, cookies_str):
        """Test deserializing of cookies."""

        assert len(cookies_str) > 0, "Cookies are empty"

        cookies = cookies_deserialize(cookies_str)

        assert isinstance(cookies, list), "Cookies are not a list"
        assert len(cookies) > 0, "Cookies list is empty"

        token = next(
            (
                cookie.get("value")
                for cookie in cookies
                if cookie.get("name") == "v-token"
            ),
            None,
        )

        assert token, "Token is None"
        assert len(token) > 0, "Token is empty"

    async def test_cookies_serialize(self):
        """Test serializing of cookies."""

        cookies_str = cookies_serialize([TEST_TOKEN_COOKIE])

        assert len(cookies_str) > 0, "Cookies are not correctly serialized"
        assert "TEST_TOKEN" in cookies_str, "Cookies do not contain TEST_TOKEN"

    async def test_cookies_merge(self, cookies_str):
        """Test merging of cookies."""

        cookies = cookies_deserialize(cookies_str)
        merged_cookies = merge_cookies(cookies, [TEST_TOKEN_COOKIE])

        assert len(cookies) == len(
            merged_cookies
        ), "Merged cookies have not the same number of cookies"

        merged_token = next(
            (
                cookie.get("value")
                for cookie in merged_cookies
                if cookie.get("name") == "v-token"
            ),
            None,
        )

        assert (
            merged_token == "TEST_TOKEN"
        ), "Merged cookies do not contain the value of the new cookie"


class TestErrorMessages:
    """Test error message functions."""

    async def test_error_message_selector(self):
        """Test error message selector function."""
        assert (
            error_message_selector("PAGE", [])
            == "Selector not found in page.\n\tPage: PAGE\n\tSelector:\n\t\t"
        ), "Error message for selected is badly formatted"
        assert (
            error_message_selector("PAGE", "SELECTOR")
            == "Selector not found in page.\n\tPage: PAGE\n\tSelector:\n\t\tSELECTOR"
        ), "Error message for selected is badly formatted"
        assert (
            error_message_selector("PAGE", ["SELECTOR1", "SELECTOR2"])
            == "Selector not found in page.\n\tPage: PAGE\n\tSelector:\n\t\tSELECTOR1\n\t\tSELECTOR2"
        ), "Error message for selected is badly formatted"


class TestResolveRemoteAddr:
    """Test resolve remote addr function."""

    @pytest.mark.parametrize(
        ("value", "result", "gethostbyname_return", "gethostbyname_raise"),
        [
            ("localhost", "localhost", None, None),
            ("1.1.1.1", "1.1.1.1", None, None),
            ("google.com", "8.8.8.8", "8.8.8.8", None),
            (
                "google.com",
                "Error resolving google.com: ERROR",
                None,
                socket.gaierror("ERROR"),
            ),
        ],
    )
    async def test_resolve_remote_addr(
        self, value, result, gethostbyname_return, gethostbyname_raise
    ):
        """Test resolve remote addr function."""

        with patch(
            "socket.gethostbyname",
            autospec=True,
            return_value=gethostbyname_return,
            side_effect=gethostbyname_raise,
        ):
            assert result == resolve_remote_addr(
                value
            ), "Result IP is not correctly resolved"


class TestTimestampedOutDir:
    """Test timestamped out dir function."""

    async def test_timestamped_out_dir(self):
        """Test timestamped out dir function."""
        path = "out_dir"
        _path = timestamped_out_dir(path)
        assert path in _path, "Original out dir path not in timestamped out dir path"
        assert "/" in _path, "Original out dir path has not been extended"


class TestCookidooSetup:
    """Test cookie setup."""

    async def test_cookidoo_setup(self, cookidoo):
        """Test setup of the cookidoo instance."""

        assert cookidoo, "Cookidoo instance has been setup up with cookies"  # Loading the instance already deserializes the test.cookies in the `conftest.py` file

        assert isinstance(
            cookidoo.cookies, str
        ), "Cookies are not correctly exported as string"

        cookidoo.cookies = "[]"

        assert (
            cookidoo.cookies == "[]"
        ), "Cookies have not been set correctly via setter"
