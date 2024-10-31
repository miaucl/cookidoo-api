"""Unit tests for cookidoo-api."""

from collections.abc import AsyncGenerator, Generator
from typing import Final

from aiohttp import ClientSession
from aioresponses import aioresponses
from dotenv import load_dotenv
import pytest

from cookidoo_api.const import DEFAULT_COOKIDOO_CONFIG
from cookidoo_api.cookidoo import Cookidoo

load_dotenv()

UUID = "00000000-00000000-00000000-00000000"

COOKIDOO_AUTH_RESPONSE: Final = {
    "access_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6ImEyYjY5NWE4LWEyZGMtM2YyOC1iODM2LTQ4YzhkYWVhMzBlZCIsInR5cCI6IkpXVCJ9.eyJhdWQiOltdLCJhdXRoX3RpbWUiOjEuNzMwMzIwMjM0ZSswOSwiYXV0aG9yaXRpZXMiOlsiUk9MRV9WT1JXRVJLQ1VTVE9NRVJHUk9VUCJdLCJjbGllbnRfaWQiOiJrdXBmZXJ3ZXJrLWNsaWVudC1ud290IiwiY2xpZW50YXBwcm92ZWQiOmZhbHNlLCJleHAiOjE3MzAzNjM0MzUsImV4dCI6eyJhdXRoX3RpbWUiOjEuNzMwMzIwMjM0ZSswOSwiYXV0aG9yaXRpZXMiOlsiUk9MRV9WT1JXRVJLQ1VTVE9NRVJHUk9VUCJdLCJjbGllbnRhcHByb3ZlZCI6ZmFsc2UsInVzZXJfbmFtZSI6ImN5cmlsbC5yYWNjYXVkK2Nvb2tpZG9vX2FwaUBnbWFpbC5jb20ifSwiZ3JhbnRfdHlwZSI6InJlZnJlc2hfdG9rZW4iLCJpYXQiOjE3MzAzMjAyMzUsImlzcyI6Imh0dHBzOi8vZXUubG9naW4udm9yd2Vyay5jb20vIiwianRpIjoiOWY5N2EyMzQtM2Y4MC00ZTM1LWJmNDgtMmUzZTllN2U4NzIwIiwibmJmIjoxNzMwMzIwMjM1LCJzY29wZSI6WyJtYXJjb3NzYXBpIiwib3BlbmlkIiwicHJvZmlsZSIsImVtYWlsIiwiT25saW5lIiwib2ZmbGluZV9hY2Nlc3MiXSwic2NwIjpbIm1hcmNvc3NhcGkiLCJvcGVuaWQiLCJwcm9maWxlIiwiZW1haWwiLCJPbmxpbmUiLCJvZmZsaW5lX2FjY2VzcyJdLCJzdWIiOiI0YTc0YzEwMi0zZWU2LTRiY2QtOTIyNy0yYzQwMzkwMGI4ZGUiLCJ1c2VyX25hbWUiOiJjeXJpbGwucmFjY2F1ZCtjb29raWRvb19hcGlAZ21haWwuY29tIn0.H64hahK91erxTb2xfM0AF17D3Ja2jSZMBvG-C8MJpjkmgG5HJxZkhZVSpF2SN5vXw1-m7gosMfJ4rwjy0wy3OOZu8wO8hDMu9c-tWidBB6XOChGKBPFONFVC5xjjEsqCDsWVEBRNlxfliKFsRCPeNNyC8WPH2wwB_gCZgPhP9hWUnC5WiYuf3iYP8C9UUK2TzcC6Zz7-CPh2_p3Qw9AOb4NFKneCiyIJcIbwiajrSN1KgVwa4C0pT7EZL_LbyaVBUzSGg5nH-TLL4ByXzwhhWKKn73Bgwq-iCgDFOhC4hDbHIWTXC2hxVX10_4XKua7tViMA90C5BDggmrXwHEitrg",
    "expires_in": 43199,
    "id_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6ImEyYjY5NWE4LWEyZGMtM2YyOC1iODM2LTQ4YzhkYWVhMzBlZCIsInR5cCI6IkpXVCJ9.eyJhY3IiOiIwIiwiYXRfaGFzaCI6IjV1QnJuMEkwZUpPbnhwM3RiLVItLWciLCJhdWQiOlsia3VwZmVyd2Vyay1jbGllbnQtbndvdCJdLCJhdXRoX3RpbWUiOjE3MzAzMjAyMzQsImJpcnRoZGF0ZSI6IjAwMDAtMDAtMDAiLCJlbWFpbCI6ImN5cmlsbC5yYWNjYXVkK2Nvb2tpZG9vX2FwaUBnbWFpbC5jb20iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwiZXhwIjoxNzMwMzYzNDM1LCJmYW1pbHlfbmFtZSI6IiIsImdpdmVuX25hbWUiOiIiLCJpYXQiOjE3MzAzMjAyMzUsImlzcyI6Imh0dHBzOi8vZXUubG9naW4udm9yd2Vyay5jb20vIiwianRpIjoiYTcwMjJmNTYtZjM2Yy00YzdjLTgwN2EtMWNkMTZmY2Q5OWJjIiwibG9jYWxlIjoiY2giLCJuYW1lIjoiIiwicHJlZmVycmVkX3VzZXJuYW1lIjoiY3lyaWxsLnJhY2NhdWQrY29va2lkb29fYXBpQGdtYWlsLmNvbSIsInByb2ZpbGUiOiIiLCJzaWQiOiIwZWEzNjhmNy0zYjBhLTQ1ZTEtODI5NS0yNThiZWU3OTdmNmYiLCJzdWIiOiI0YTc0YzEwMi0zZWU2LTRiY2QtOTIyNy0yYzQwMzkwMGI4ZGUifQ.cBJQSfsoIy8ZdVnRuEW2HYhG0MrX7QBa9s_I-Z9jwkwfA9FF_9Zv3e-XY4JBURPERYEoXHlR-KS14CdNZTIAEZgi7FxmoBU9cOwGHbMlb2mWv-O8TAivgCEquZWzjxPwOV7pknteCuEm_C-egWSx3bh6tHIqrrDPjh9RX5mNrfzxDWjDOgOMeQDhS1OoHrsVO6ndBHXEQojEpJLSAOxBoDOuK0KDSfM5Ji5GpBKHBLDTDcHebkruX7Ps4HWOgBvYrJiqz2Fc3hy01dmFJ8ThPKVYAD6Q28hM9pTXIzHQ41jiEryl1RqV4mPhivXufsYzBXXSUwFi_p6w3obyohQYcg",
    "iss": "https://eu.login.vorwerk.com/",
    "jti": "9f97a234-3f80-4e35-bf48-2e3e9e7e8720",
    "refresh_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6ImEyYjY5NWE4LWEyZGMtM2YyOC1iODM2LTQ4YzhkYWVhMzBlZCIsInR5cCI6IkpXVCJ9.eyJhdGkiOiIwZGU0MmM3YS1mMzM0LTQ4ZjItYTRjOS0wMTA0NTcwZDI4MTUiLCJhdWQiOltdLCJhdXRoX3RpbWUiOjEuNzMwMzIwMjM0ZSswOSwiYXV0aG9yaXRpZXMiOlsiUk9MRV9WT1JXRVJLQ1VTVE9NRVJHUk9VUCJdLCJjbGllbnRfaWQiOiJrdXBmZXJ3ZXJrLWNsaWVudC1ud290IiwiY2xpZW50YXBwcm92ZWQiOmZhbHNlLCJleHAiOjE3MzI5MTIyMzUsImV4dCI6eyJhdXRoX3RpbWUiOjEuNzMwMzIwMjM0ZSswOSwiYXV0aG9yaXRpZXMiOlsiUk9MRV9WT1JXRVJLQ1VTVE9NRVJHUk9VUCJdLCJjbGllbnRhcHByb3ZlZCI6ZmFsc2UsInVzZXJfbmFtZSI6ImN5cmlsbC5yYWNjYXVkK2Nvb2tpZG9vX2FwaUBnbWFpbC5jb20ifSwiZ3JhbnRfdHlwZSI6InJlZnJlc2hfdG9rZW4iLCJpYXQiOjE3MzAzMjAyMzUsImlzcyI6Imh0dHBzOi8vZXUubG9naW4udm9yd2Vyay5jb20vIiwianRpIjoiMGRlNDJjN2EtZjMzNC00OGYyLWE0YzktMDEwNDU3MGQyODE1IiwibmJmIjoxNzMwMzIwMjM1LCJzY29wZSI6WyJtYXJjb3NzYXBpIiwib3BlbmlkIiwicHJvZmlsZSIsImVtYWlsIiwiT25saW5lIiwib2ZmbGluZV9hY2Nlc3MiXSwic2NwIjpbIm1hcmNvc3NhcGkiLCJvcGVuaWQiLCJwcm9maWxlIiwiZW1haWwiLCJPbmxpbmUiLCJvZmZsaW5lX2FjY2VzcyJdLCJzdWIiOiI0YTc0YzEwMi0zZWU2LTRiY2QtOTIyNy0yYzQwMzkwMGI4ZGUiLCJ1c2VyX25hbWUiOiJjeXJpbGwucmFjY2F1ZCtjb29raWRvb19hcGlAZ21haWwuY29tIn0.srvwIOW2w5rlTTvX6640WMrf0eLFBX5k-6_ZSSF8pYBR0KuHjc4Z53cPWx5YpIjnSB_SKVLXrAlnU7ouJfGXbFe3Fpq2WS9zbNEJEVK50n8--kpzYoWaDQXOoHOxfLfQJvjORl6YD_5sOmNRuc0444NcEzmwFctrnVNy6TADKVrqvmrVI8YD1APX6-QEka9jvPIe7enHDvEwmj54tge4XfaeMeGoGhjJZab4vgtsRFwS6WYu92yTzP4hh_o0fUVspeYTdhrapg3FVKFJ1i4txjCw2W9KsmbYlU4P1JCogH7Luq7CVSRFcoJcSDSBY3Gx43W34LAj-0JLIfnV9CX5ug",
    "scope": "marcossapi openid profile email Online offline_access",
    "token_type": "bearer",
    "user_name": "your@email",
}

COOKIDOO_USER_INFO: Final = {
    "id": UUID,
    "isPublic": False,
    "userInfo": {
        "username": "Test User",
        "description": "",
        "picture": "",
        "pictureTemplate": "",
    },
    "savedSearches": [
        {
            "id": "default",
            "search": {
                "countries": ["ch"],
                "languages": ["de"],
                "accessories": [
                    "includingFriend",
                    "includingBladeCover",
                    "includingBladeCoverWithPeeler",
                    "includingCutter",
                    "includingSensor",
                ],
            },
        }
    ],
    "foodPreferences": [],
    "meta": {
        "cloudinaryPublicId": "61c22d8465a60c86de8ca7ce045665bfa35546d78ba6f971ffbed3780d4fa026"
    },
    "thermomixes": [],
}

COOKIDOO_ACTIVE_SUBSCRIPTION: Final = [
    {
        "active": True,
        "startDate": "2024-09-15T00:00:00Z",
        "expires": "2024-10-15T23:59:00Z",
        "type": "TRIAL",
        "extendedType": "TRIAL",
        "autoRenewalProduct": "Cookidoo 1 Month Free",
        "autoRenewalProductCode": None,
        "countryOfResidence": "ch",
        "subscriptionLevel": "NONE",
        "status": "RUNNING",
        "marketMismatch": False,
        "subscriptionSource": "COMMERCE",
        "_created": "2024-10-30T15:38:26.496029003Z",
        "_modified": None,
    }
]

COOKIDOO_INACTIVE_SUBSCRIPTION: Final = [
    {
        "active": False,
        "startDate": "2024-09-15T00:00:00Z",
        "expires": "2024-10-15T23:59:00Z",
        "type": "TRIAL",
        "extendedType": "TRIAL",
        "autoRenewalProduct": "Cookidoo 1 Month Free",
        "autoRenewalProductCode": None,
        "countryOfResidence": "ch",
        "subscriptionLevel": "NONE",
        "status": "ENDED",
        "marketMismatch": False,
        "subscriptionSource": "COMMERCE",
        "_created": "2024-10-30T15:38:26.496029003Z",
        "_modified": None,
    }
]


@pytest.fixture(name="session")
async def aiohttp_client_session() -> AsyncGenerator[ClientSession]:
    """Create  a client session."""
    async with ClientSession() as session:
        yield session


@pytest.fixture(name="cookidoo")
async def bring_api_client(session: ClientSession) -> Cookidoo:
    """Create Cookidoo instance."""
    bring = Cookidoo(session, DEFAULT_COOKIDOO_CONFIG)
    return bring


@pytest.fixture(name="mocked")
def aioclient_mock() -> Generator[aioresponses]:
    """Mock Aiohttp client requests."""
    with aioresponses() as m:
        yield m
