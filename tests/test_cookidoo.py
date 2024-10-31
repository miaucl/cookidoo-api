"""Unit tests for cookidoo-api."""

from http import HTTPStatus

from aiohttp import ClientError
from aioresponses import aioresponses
from dotenv import load_dotenv
import pytest

from cookidoo_api.cookidoo import Cookidoo
from cookidoo_api.exceptions import (
    CookidooAuthException,
    CookidooConfigException,
    CookidooParseException,
    CookidooRequestException,
)
from tests.conftest import (
    COOKIDOO_ACTIVE_SUBSCRIPTION,
    COOKIDOO_AUTH_RESPONSE,
    COOKIDOO_INACTIVE_SUBSCRIPTION,
    COOKIDOO_USER_INFO,
)

load_dotenv()


class TestLogin:
    """Tests for login method."""

    async def test_refresh_before_login(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test refresh before login."""
        mocked.post(
            "https://eu.login.vorwerk.com/oauth2/token",
            status=400,
        )
        expected = "No auth data available, please log in first"
        with pytest.raises(CookidooConfigException, match=expected):
            await cookidoo.refresh_token()

    async def test_mail_invalid(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test login with invalid e-mail."""
        mocked.post(
            "https://eu.login.vorwerk.com/oauth2/token",
            status=400,
        )
        expected = "Access token request failed due to bad request, please check your email or refresh token."
        with pytest.raises(CookidooAuthException, match=expected):
            await cookidoo.login()

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test login with unauthorized user."""
        mocked.post(
            "https://eu.login.vorwerk.com/oauth2/token",
            status=HTTPStatus.UNAUTHORIZED,
            payload={"error_description": ""},
        )
        expected = "Access token request failed due to authorization failure, please check your email and password or refresh token."
        with pytest.raises(CookidooAuthException, match=expected):
            await cookidoo.login()

    @pytest.mark.parametrize("status", [HTTPStatus.OK, HTTPStatus.UNAUTHORIZED])
    async def test_parse_exception(
        self, mocked: aioresponses, cookidoo: Cookidoo, status: HTTPStatus
    ) -> None:
        """Test parse exceptions."""
        mocked.post(
            "https://eu.login.vorwerk.com/oauth2/token",
            status=status,
            body="not json",
            content_type="application/json",
        )

        with pytest.raises(CookidooParseException):
            await cookidoo.login()

    @pytest.mark.parametrize(
        "exception",
        [
            TimeoutError,
            ClientError,
        ],
    )
    async def test_request_exceptions(
        self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception
    ) -> None:
        """Test exceptions."""
        mocked.post("https://eu.login.vorwerk.com/oauth2/token", exception=exception)
        with pytest.raises(CookidooRequestException):
            await cookidoo.login()

    async def test_login_and_refresh(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test login and refresh with valid user."""

        mocked.post(
            "https://eu.login.vorwerk.com/oauth2/token",
            status=HTTPStatus.OK,
            payload=COOKIDOO_AUTH_RESPONSE,
        )

        data = await cookidoo.login()
        for key, value in data.items():
            assert value == COOKIDOO_AUTH_RESPONSE[key]
        assert cookidoo.expires_in > 0

        mocked.post(
            "https://eu.login.vorwerk.com/oauth2/token",
            status=HTTPStatus.OK,
            payload=COOKIDOO_AUTH_RESPONSE,
        )

        data = await cookidoo.refresh_token()
        for key, value in data.items():
            assert value == COOKIDOO_AUTH_RESPONSE[key]
        assert cookidoo.expires_in > 0


class TestGetUserInfo:
    """Tests for get_user_info method."""

    async def test_get_user_info(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for get_user_info."""

        mocked.get(
            "https://ch.tmmobile.vorwerk-digital.com/community/profile",
            payload=COOKIDOO_USER_INFO,
            status=HTTPStatus.OK,
        )

        data = await cookidoo.get_user_info()
        assert data["username"] == COOKIDOO_USER_INFO["userInfo"]["username"]  # type: ignore[index]
        assert data["description"] == COOKIDOO_USER_INFO["userInfo"]["description"]  # type: ignore[index]
        assert data["picture"] == COOKIDOO_USER_INFO["userInfo"]["picture"]  # type: ignore[index]

    @pytest.mark.parametrize(
        "exception",
        [
            TimeoutError,
            ClientError,
        ],
    )
    async def test_request_exception(
        self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception
    ) -> None:
        """Test request exceptions."""

        mocked.get(
            "https://ch.tmmobile.vorwerk-digital.com/community/profile",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.get_user_info()

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.get(
            "https://ch.tmmobile.vorwerk-digital.com/community/profile",
            status=HTTPStatus.UNAUTHORIZED,
            payload={"error_description": ""},
        )
        with pytest.raises(CookidooAuthException):
            await cookidoo.get_user_info()

    @pytest.mark.parametrize("status", [HTTPStatus.OK, HTTPStatus.UNAUTHORIZED])
    async def test_parse_exception(
        self, mocked: aioresponses, cookidoo: Cookidoo, status: HTTPStatus
    ) -> None:
        """Test parse exceptions."""
        mocked.get(
            "https://ch.tmmobile.vorwerk-digital.com/community/profile",
            status=status,
            body="not json",
            content_type="application/json",
        )

        with pytest.raises(CookidooParseException):
            await cookidoo.get_user_info()


class TestGetActiveSubscription:
    """Tests for get_active_subscription method."""

    async def test_get_active_subscription(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for get_active_subscription."""

        mocked.get(
            "https://ch.tmmobile.vorwerk-digital.com/ownership/subscriptions",
            payload=COOKIDOO_ACTIVE_SUBSCRIPTION,
            status=HTTPStatus.OK,
        )

        data = await cookidoo.get_active_subscription()
        assert data
        assert data["active"]
        assert data["status"] == "RUNNING"

    async def test_get_inactive_subscription(
        self, mocked: aioresponses, cookidoo: Cookidoo
    ) -> None:
        """Test for get_active_subscription."""

        mocked.get(
            "https://ch.tmmobile.vorwerk-digital.com/ownership/subscriptions",
            payload=COOKIDOO_INACTIVE_SUBSCRIPTION,
            status=HTTPStatus.OK,
        )

        data = await cookidoo.get_active_subscription()
        assert data is None

    @pytest.mark.parametrize(
        "exception",
        [
            TimeoutError,
            ClientError,
        ],
    )
    async def test_request_exception(
        self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception
    ) -> None:
        """Test request exceptions."""

        mocked.get(
            "https://ch.tmmobile.vorwerk-digital.com/ownership/subscriptions",
            exception=exception,
        )

        with pytest.raises(CookidooRequestException):
            await cookidoo.get_active_subscription()

    async def test_unauthorized(self, mocked: aioresponses, cookidoo: Cookidoo) -> None:
        """Test unauthorized exception."""
        mocked.get(
            "https://ch.tmmobile.vorwerk-digital.com/ownership/subscriptions",
            status=HTTPStatus.UNAUTHORIZED,
            payload={"error_description": ""},
        )
        with pytest.raises(CookidooAuthException):
            await cookidoo.get_active_subscription()

    @pytest.mark.parametrize("status", [HTTPStatus.OK, HTTPStatus.UNAUTHORIZED])
    async def test_parse_exception(
        self, mocked: aioresponses, cookidoo: Cookidoo, status: HTTPStatus
    ) -> None:
        """Test parse exceptions."""
        mocked.get(
            "https://ch.tmmobile.vorwerk-digital.com/ownership/subscriptions",
            status=status,
            body="not json",
            content_type="application/json",
        )

        with pytest.raises(CookidooParseException):
            await cookidoo.get_active_subscription()


# class TestLoadLists:
#     """Tests for load_lists method."""

#     async def test_load_lists(self, cookidoo, mocked, monkeypatch):
#         """Test load_lists."""

#         mocked.get(
#             f"https://api.getcookidoo.com/rest/cookidoousers/{UUID}/lists",
#             status=HTTPStatus.OK,
#             payload=BRING_LOAD_LISTS_RESPONSE,
#         )
#         monkeypatch.setattr(cookidoo, "uuid", UUID)

#         lists = await cookidoo.load_lists()

#         assert lists == BRING_LOAD_LISTS_RESPONSE

#     @pytest.mark.parametrize("status", [HTTPStatus.OK, HTTPStatus.UNAUTHORIZED])
#     async def test_parse_exception(self, mocked:aioresponses, cookidoo: Cookidoo, monkeypatch, status):
#         """Test parse exceptions."""
#         mocked.get(
#             f"https://api.getcookidoo.com/rest/cookidoousers/{UUID}/lists",
#             status=status,
#             body="not json",
#             content_type="application/json",
#         )
#         monkeypatch.setattr(cookidoo, "uuid", UUID)

#         with pytest.raises(CookidooParseException):
#             await cookidoo.load_lists()

#     async def test_unauthorized(self, mocked:aioresponses, cookidoo: Cookidoo, monkeypatch):
#         """Test unauthorized exception."""
#         mocked.get(
#             f"https://api.getcookidoo.com/rest/cookidoousers/{UUID}/lists",
#             status=HTTPStatus.UNAUTHORIZED,
#             payload={"error_description": ""},
#         )
#         monkeypatch.setattr(cookidoo, "uuid", UUID)
#         with pytest.raises(CookidooAuthException):
#             await cookidoo.load_lists()

#     @pytest.mark.parametrize(
#         "exception",
#         [
#             asyncio.TimeoutError,
#             aiohttp.ClientError,
#         ],
#     )
#     async def test_request_exception(self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception, monkeypatch):
#         """Test request exceptions."""
#         mocked.get(
#             f"https://api.getcookidoo.com/rest/cookidoousers/{UUID}/lists",
#             exception=exception,
#         )
#         monkeypatch.setattr(cookidoo, "uuid", UUID)

#         with pytest.raises(CookidooRequestException):
#             await cookidoo.load_lists()


# class TestNotifications:
#     """Tests for notification method."""

#     @pytest.mark.parametrize(
#         ("notification_type", "item_name"),
#         [
#             (CookidooNotificationType.GOING_SHOPPING, ""),
#             (CookidooNotificationType.CHANGED_LIST, ""),
#             (CookidooNotificationType.SHOPPING_DONE, ""),
#             (CookidooNotificationType.URGENT_MESSAGE, "WITH_ITEM_NAME"),
#         ],
#     )
#     async def test_notify(
#         self,
#         cookidoo,
#         notification_type: CookidooNotificationType,
#         item_name: str,
#         mocked,
#     ):
#         """Test GOING_SHOPPING notification."""

#         mocked.post(
#             f"https://api.getcookidoo.com/rest/v2/cookidoonotifications/lists/{UUID}",
#             status=HTTPStatus.OK,
#         )
#         resp = await cookidoo.notify(UUID, notification_type, item_name)
#         assert resp.status == HTTPStatus.OK

#     async def test_notify_urgent_message_item_name_missing(self, cookidoo, mocked):
#         """Test URGENT_MESSAGE notification."""
#         mocked.post(
#             f"https://api.getcookidoo.com/rest/v2/cookidoonotifications/lists/{UUID}",
#             status=HTTPStatus.OK,
#         )
#         with pytest.raises(
#             ValueError,
#             match="notificationType is URGENT_MESSAGE but argument itemName missing.",
#         ):
#             await cookidoo.notify(UUID, CookidooNotificationType.URGENT_MESSAGE, "")

#     async def test_notify_notification_type_raise_attribute_error(
#         self, cookidoo, mocked
#     ):
#         """Test URGENT_MESSAGE notification."""

#         with pytest.raises(
#             AttributeError,
#         ):
#             await cookidoo.notify(UUID, "STRING", "")

#     async def test_notify_notification_type_raise_type_error(self, cookidoo, mocked):
#         """Test URGENT_MESSAGE notification."""

#         class WrongEnum(enum.Enum):
#             """Test Enum."""

#             UNKNOWN = "UNKNOWN"

#         with pytest.raises(
#             TypeError,
#             match="notificationType WrongEnum.UNKNOWN not supported,"
#             "must be of type CookidooNotificationType.",
#         ):
#             await cookidoo.notify(UUID, WrongEnum.UNKNOWN, "")

#     @pytest.mark.parametrize(
#         "exception",
#         [
#             asyncio.TimeoutError,
#             aiohttp.ClientError,
#         ],
#     )
#     async def test_request_exception(self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception):
#         """Test request exceptions."""

#         mocked.post(
#             f"https://api.getcookidoo.com/rest/v2/cookidoonotifications/lists/{UUID}",
#             exception=exception,
#         )

#         with pytest.raises(CookidooRequestException):
#             await cookidoo.notify(UUID, CookidooNotificationType.GOING_SHOPPING)

#     async def test_unauthorized(self, mocked:aioresponses, cookidoo: Cookidoo):
#         """Test unauthorized exception."""
#         mocked.post(
#             f"https://api.getcookidoo.com/rest/v2/cookidoonotifications/lists/{UUID}",
#             status=HTTPStatus.UNAUTHORIZED,
#             payload={"error_description": ""},
#         )
#         with pytest.raises(CookidooAuthException):
#             await cookidoo.notify(UUID, CookidooNotificationType.GOING_SHOPPING)

#     async def test_parse_exception(self, mocked:aioresponses, cookidoo: Cookidoo):
#         """Test parse exceptions."""
#         mocked.post(
#             f"https://api.getcookidoo.com/rest/v2/cookidoonotifications/lists/{UUID}",
#             status=HTTPStatus.UNAUTHORIZED,
#             body="not json",
#             content_type="application/json",
#         )

#         with pytest.raises(CookidooParseException):
#             await cookidoo.notify(UUID, CookidooNotificationType.GOING_SHOPPING)


# class TestGetList:
#     """Tests for get_list method."""

#     @pytest.mark.parametrize(
#         "exception",
#         [
#             asyncio.TimeoutError,
#             aiohttp.ClientError,
#         ],
#     )
#     async def test_request_exception(self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception):
#         """Test request exceptions."""

#         mocked.get(
#             f"https://api.getcookidoo.com/rest/v2/cookidoolists/{UUID}",
#             exception=exception,
#         )

#         with pytest.raises(CookidooRequestException):
#             await cookidoo.get_list(UUID)

#     async def test_unauthorized(self, mocked:aioresponses, cookidoo: Cookidoo):
#         """Test unauthorized exception."""
#         mocked.get(
#             f"https://api.getcookidoo.com/rest/v2/cookidoolists/{UUID}",
#             status=HTTPStatus.UNAUTHORIZED,
#             payload={"error_description": ""},
#         )
#         with pytest.raises(CookidooAuthException):
#             await cookidoo.get_list(UUID)

#     @pytest.mark.parametrize("status", [HTTPStatus.OK, HTTPStatus.UNAUTHORIZED])
#     async def test_parse_exception(self, mocked:aioresponses, cookidoo: Cookidoo, monkeypatch, status):
#         """Test parse exceptions."""
#         mocked.get(
#             f"https://api.getcookidoo.com/rest/v2/cookidoolists/{UUID}",
#             status=status,
#             body="not json",
#             content_type="application/json",
#         )
#         monkeypatch.setattr(cookidoo, "uuid", UUID)

#         with pytest.raises(CookidooParseException):
#             await cookidoo.get_list(UUID)

#     async def test_get_list(self, mocked:aioresponses, cookidoo: Cookidoo, monkeypatch):
#         """Test get list."""
#         mocked.get(
#             f"https://api.getcookidoo.com/rest/v2/cookidoolists/{UUID}",
#             status=HTTPStatus.OK,
#             payload=BRING_GET_LIST_RESPONSE,
#         )

#         monkeypatch.setattr(Cookidoo, "_Cookidoo__locale", lambda _, x: "de-DE")
#         monkeypatch.setattr(Cookidoo, "_Cookidoo__translate", mocked_translate)
#         monkeypatch.setattr(cookidoo, "uuid", UUID)

#         data = await cookidoo.get_list(UUID)
#         assert data == {
#             "uuid": BRING_GET_LIST_RESPONSE["uuid"],
#             "status": BRING_GET_LIST_RESPONSE["status"],
#             **BRING_GET_LIST_RESPONSE["items"],
#         }


# class TestGetAllItemDetails:
#     """Test for get_all_item_details method."""

#     async def test_get_all_item_details(self, mocked:aioresponses, cookidoo: Cookidoo):
#         """Test get_all_item_details."""
#         mocked.get(
#             f"https://api.getcookidoo.com/rest/cookidoolists/{UUID}/details",
#             status=HTTPStatus.OK,
#             payload=BRING_GET_ALL_ITEM_DETAILS_RESPONSE,
#         )

#         data = await cookidoo.get_all_item_details(UUID)
#         assert data == BRING_GET_ALL_ITEM_DETAILS_RESPONSE

#     async def test_list_not_found(self, mocked:aioresponses, cookidoo: Cookidoo):
#         """Test get_all_item_details."""
#         mocked.get(
#             f"https://api.getcookidoo.com/rest/cookidoolists/{UUID}/details",
#             status=404,
#             reason=f"List with uuid '{UUID}' not found",
#         )

#         with pytest.raises(CookidooRequestException):
#             await cookidoo.get_all_item_details(UUID)

#     async def test_unauthorized(self, mocked:aioresponses, cookidoo: Cookidoo):
#         """Test unauthorized exception."""
#         mocked.get(
#             f"https://api.getcookidoo.com/rest/cookidoolists/{UUID}/details",
#             status=HTTPStatus.UNAUTHORIZED,
#             payload={"error_description": ""},
#         )
#         with pytest.raises(CookidooAuthException):
#             await cookidoo.get_all_item_details(UUID)

#     @pytest.mark.parametrize("status", [HTTPStatus.OK, HTTPStatus.UNAUTHORIZED])
#     async def test_parse_exception(self, mocked: aioresponses, cookidoo: Cookidoo, status: HTTPStatus):
#         """Test parse exceptions."""
#         mocked.get(
#             f"https://api.getcookidoo.com/rest/cookidoolists/{UUID}/details",
#             status=status,
#             body="not json",
#             content_type="application/json",
#         )

#         with pytest.raises(CookidooParseException):
#             await cookidoo.get_all_item_details(UUID)

#     @pytest.mark.parametrize(
#         "exception",
#         [
#             asyncio.TimeoutError,
#             aiohttp.ClientError,
#         ],
#     )
#     async def test_request_exception(self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception):
#         """Test request exceptions."""

#         mocked.get(
#             f"https://api.getcookidoo.com/rest/cookidoolists/{UUID}/details",
#             exception=exception,
#         )

#         with pytest.raises(CookidooRequestException):
#             await cookidoo.get_all_item_details(UUID)


# async def mocked_batch_update_list(
#     cookidoo: Cookidoo,
#     list_uuid: str,
#     items: CookidooItem,
#     operation: CookidooItemOperation,
# ):
#     """Mock batch_update_list."""
#     return (list_uuid, items, operation)


# class TestSaveItem:
#     """Test for save_item method."""

#     @pytest.mark.parametrize(
#         ("item_name", "specification", "item_uuid"),
#         [
#             ("item name", "", None),
#             ("item name", "specification", None),
#             ("item name", "", UUID),
#         ],
#     )
#     async def test_save_item(
#         self, cookidoo, monkeypatch, item_name, specification, item_uuid
#     ):
#         """Test save_item."""

#         monkeypatch.setattr(Cookidoo, "batch_update_list", mocked_batch_update_list)

#         list_uuid, items, operation = await cookidoo.save_item(
#             UUID, item_name, specification, item_uuid
#         )
#         assert list_uuid == UUID
#         expected = {"itemId": item_name, "spec": specification, "uuid": item_uuid}
#         assert expected == items
#         assert operation == CookidooItemOperation.ADD

#     @pytest.mark.parametrize(
#         "exception",
#         [
#             asyncio.TimeoutError,
#             aiohttp.ClientError,
#         ],
#     )
#     async def test_request_exception(self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception):
#         """Test request exceptions."""

#         mocked.put(
#             f"https://api.getcookidoo.com/rest/v2/cookidoolists/{UUID}/items",
#             exception=exception,
#         )

#         with pytest.raises(CookidooRequestException) as exc:
#             await cookidoo.save_item(UUID, "item_name", "specification")
#         assert (
#             exc.value.args[0]
#             == f"Saving item item_name (specification) to list {UUID} "
#             "failed due to request exception."
#         )


# class TestUpdateItem:
#     """Test for save_item method."""

#     @pytest.mark.parametrize(
#         ("item_name", "specification", "item_uuid"),
#         [
#             ("item name", "", None),
#             ("item name", "specification", None),
#             ("item name", "", UUID),
#         ],
#     )
#     async def test_update_item(
#         self, cookidoo, monkeypatch, item_name, specification, item_uuid
#     ):
#         """Test save_item."""

#         monkeypatch.setattr(Cookidoo, "batch_update_list", mocked_batch_update_list)

#         list_uuid, items, operation = await cookidoo.update_item(
#             UUID, item_name, specification, item_uuid
#         )
#         assert list_uuid == UUID
#         expected = {"itemId": item_name, "spec": specification, "uuid": item_uuid}
#         assert expected == items
#         assert operation == CookidooItemOperation.ADD

#     @pytest.mark.parametrize(
#         "exception",
#         [
#             asyncio.TimeoutError,
#             aiohttp.ClientError,
#         ],
#     )
#     async def test_request_exception(self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception):
#         """Test request exceptions."""

#         mocked.put(
#             f"https://api.getcookidoo.com/rest/v2/cookidoolists/{UUID}/items",
#             exception=exception,
#         )

#         with pytest.raises(CookidooRequestException) as exc:
#             await cookidoo.update_item(UUID, "item_name", "specification")
#         assert (
#             exc.value.args[0]
#             == f"Updating item item_name (specification) in list {UUID} "
#             "failed due to request exception."
#         )


# class TestRemoveItem:
#     """Test for save_item method."""

#     @pytest.mark.parametrize(
#         ("item_name", "item_uuid"),
#         [
#             ("item name", None),
#             ("item name", UUID),
#         ],
#     )
#     async def test_remove_item(self, cookidoo, monkeypatch, item_name, item_uuid):
#         """Test save_item."""

#         monkeypatch.setattr(Cookidoo, "batch_update_list", mocked_batch_update_list)

#         list_uuid, items, operation = await cookidoo.remove_item(
#             UUID, item_name, item_uuid
#         )
#         assert list_uuid == UUID
#         expected = {"itemId": item_name, "spec": "", "uuid": item_uuid}
#         assert expected == items
#         assert operation == CookidooItemOperation.REMOVE

#     @pytest.mark.parametrize(
#         "exception",
#         [
#             asyncio.TimeoutError,
#             aiohttp.ClientError,
#         ],
#     )
#     async def test_request_exception(self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception):
#         """Test request exceptions."""

#         mocked.put(
#             f"https://api.getcookidoo.com/rest/v2/cookidoolists/{UUID}/items",
#             exception=exception,
#         )

#         with pytest.raises(CookidooRequestException) as exc:
#             await cookidoo.remove_item(UUID, "item_name")
#         assert (
#             exc.value.args[0] == f"Removing item item_name from list {UUID} "
#             "failed due to request exception."
#         )


# class TestCompleteItem:
#     """Test for save_item method."""

#     @pytest.mark.parametrize(
#         ("item_name", "specification", "item_uuid"),
#         [
#             ("item name", "", None),
#             ("item name", "specification", None),
#             ("item name", "", UUID),
#         ],
#     )
#     async def test_complete_item(
#         self, cookidoo, monkeypatch, item_name, specification, item_uuid
#     ):
#         """Test save_item."""

#         monkeypatch.setattr(Cookidoo, "batch_update_list", mocked_batch_update_list)

#         list_uuid, items, operation = await cookidoo.complete_item(
#             UUID, item_name, specification, item_uuid
#         )
#         assert list_uuid == UUID
#         expected = {"itemId": item_name, "spec": specification, "uuid": item_uuid}
#         assert expected == items
#         assert operation == CookidooItemOperation.COMPLETE

#     @pytest.mark.parametrize(
#         "exception",
#         [
#             asyncio.TimeoutError,
#             aiohttp.ClientError,
#         ],
#     )
#     async def test_request_exception(self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception):
#         """Test request exceptions."""

#         mocked.put(
#             f"https://api.getcookidoo.com/rest/v2/cookidoolists/{UUID}/items",
#             exception=exception,
#         )

#         with pytest.raises(CookidooRequestException) as exc:
#             await cookidoo.complete_item(UUID, "item_name")
#         assert (
#             exc.value.args[0] == f"Completing item item_name from list {UUID} "
#             "failed due to request exception."
#         )


# class TestArticleTranslations:
#     """Test loading of article translation tables."""

#     def mocked__load_article_translations_from_file(self, locale):
#         """Mock and raise for fallback to ressource download."""
#         raise OSError()

#     def test_load_file(self, cookidoo, mocked):
#         """Test loading json from file."""

#         dictionary = cookidoo._Cookidoo__load_article_translations_from_file("de-CH")

#         assert "Pouletbrüstli" in dictionary
#         assert dictionary["Pouletbrüstli"] == "Pouletbrüstli"
#         assert len(dictionary) == 444

#     async def test_load_from_list_article_language(self, cookidoo, monkeypatch):
#         """Test loading json from listArticleLanguage."""

#         monkeypatch.setattr(
#             cookidoo, "user_list_settings", {UUID: {"listArticleLanguage": "de-DE"}}
#         )

#         dictionaries = await cookidoo._Cookidoo__load_article_translations()

#         assert "de-DE" in dictionaries
#         assert dictionaries["de-DE"]["Pouletbrüstli"] == "Hähnchenbrust"
#         assert len(dictionaries["de-DE"]) == 444

#     async def test_load_from_user_locale(self, cookidoo, monkeypatch):
#         """Test loading json from user_locale."""

#         monkeypatch.setattr(cookidoo, "user_locale", "de-DE")

#         dictionaries = await cookidoo._Cookidoo__load_article_translations()

#         assert "de-DE" in dictionaries
#         assert dictionaries["de-DE"]["Pouletbrüstli"] == "Hähnchenbrust"
#         assert len(dictionaries["de-DE"]) == 444

#     @pytest.mark.parametrize(
#         ("test_locale", "expected_locale"),
#         [
#             ("de-XX", "de-DE"),
#             ("en-XX", "en-US"),
#             ("es-XX", "es-ES"),
#             ("de-DE", "de-DE"),
#             ("en-GB", "en-GB"),
#         ],
#     )
#     async def test_map_user_language_to_locale(
#         self, cookidoo, test_locale, expected_locale
#     ):
#         """Test mapping invalid user_locale to valid locale."""

#         user_locale = {"language": test_locale[0:2], "country": test_locale[3:5]}
#         locale = cookidoo.map_user_language_to_locale(user_locale)

#         assert expected_locale == locale

#     def test_get_locale_from_list(self, cookidoo, monkeypatch):
#         """Test get locale from list."""

#         monkeypatch.setattr(
#             cookidoo, "user_list_settings", {UUID: {"listArticleLanguage": "de-DE"}}
#         )
#         monkeypatch.setattr(cookidoo, "user_locale", "es-ES")
#         locale = cookidoo._Cookidoo__locale(UUID)

#         assert locale == "de-DE"

#     def test_get_locale_from_user(self, cookidoo, monkeypatch):
#         """Test get locale from user_locale."""

#         monkeypatch.setattr(
#             cookidoo, "user_list_settings", {UUID: {"listArticleLanguage": "de-DE"}}
#         )
#         monkeypatch.setattr(cookidoo, "user_locale", "es-ES")
#         locale = cookidoo._Cookidoo__locale("xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxx")

#         assert locale == "es-ES"

#     def test_get_locale_from_list_fallback(self, cookidoo, monkeypatch):
#         """Test get locale from list and fallback to user_locale."""

#         monkeypatch.setattr(cookidoo, "user_list_settings", {UUID: {}})
#         monkeypatch.setattr(cookidoo, "user_locale", "es-ES")
#         locale = cookidoo._Cookidoo__locale(UUID)

#         assert locale == "es-ES"

#     async def test_load_all_locales(self, cookidoo, monkeypatch):
#         """Test loading all locales."""

#         user_list_settings = {
#             k: {"listArticleLanguage": v} for k, v in enumerate(BRING_SUPPORTED_LOCALES)
#         }

#         monkeypatch.setattr(cookidoo, "user_list_settings", user_list_settings)
#         dictionaries = await cookidoo._Cookidoo__load_article_translations()

#         assert len(dictionaries) == 19  # de-CH is skipped

#     async def test_load_fallback_to_download(self, cookidoo, mocked, monkeypatch):
#         """Test loading json and fallback to download from web."""
#         mocked.get(
#             "https://web.getcookidoo.com/locale/articles.de-DE.json",
#             payload={"test": "test"},
#             status=HTTPStatus.OK,
#         )

#         monkeypatch.setattr(cookidoo, "user_locale", "de-DE")

#         monkeypatch.setattr(
#             Cookidoo,
#             "_Cookidoo__load_article_translations_from_file",
#             self.mocked__load_article_translations_from_file,
#         )

#         dictionaries = await cookidoo._Cookidoo__load_article_translations()

#         assert dictionaries["de-DE"] == {"test": "test"}

#     @pytest.mark.parametrize(
#         "exception",
#         [
#             asyncio.TimeoutError,
#             aiohttp.ClientError,
#         ],
#     )
#     async def test_request_exceptions(self, cookidoo, mocked, monkeypatch, exception):
#         """Test loading json and fallback to download from web."""
#         mocked.get(
#             "https://web.getcookidoo.com/locale/articles.de-DE.json",
#             exception=exception,
#         )

#         monkeypatch.setattr(cookidoo, "user_locale", "de-DE")

#         monkeypatch.setattr(
#             Cookidoo,
#             "_Cookidoo__load_article_translations_from_file",
#             self.mocked__load_article_translations_from_file,
#         )
#         with pytest.raises(CookidooRequestException):
#             await cookidoo._Cookidoo__load_article_translations()

#     async def test_parse_exception(self, cookidoo, mocked, monkeypatch):
#         """Test loading json and fallback to download from web."""
#         mocked.get(
#             "https://web.getcookidoo.com/locale/articles.de-DE.json",
#             status=HTTPStatus.OK,
#             body="not json",
#             content_type="application/json",
#         )

#         monkeypatch.setattr(cookidoo, "user_locale", "de-DE")

#         monkeypatch.setattr(
#             Cookidoo,
#             "_Cookidoo__load_article_translations_from_file",
#             self.mocked__load_article_translations_from_file,
#         )
#         with pytest.raises(CookidooParseException):
#             await cookidoo._Cookidoo__load_article_translations()


# class TestGetUserAccount:
#     """Tests for get_user_account method."""

#     async def test_get_user_account(self, cookidoo, mocked, monkeypatch):
#         """Test for get_user_account."""

#         mocked.get(
#             f"https://api.getcookidoo.com/rest/v2/cookidoousers/{UUID}",
#             payload=BRING_USER_ACCOUNT_RESPONSE,
#             status=HTTPStatus.OK,
#         )

#         monkeypatch.setattr(cookidoo, "uuid", UUID)
#         data = await cookidoo.get_user_account()

#         assert data == BRING_USER_ACCOUNT_RESPONSE

#     @pytest.mark.parametrize(
#         "exception",
#         [
#             asyncio.TimeoutError,
#             aiohttp.ClientError,
#         ],
#     )
#     async def test_request_exception(self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception, monkeypatch):
#         """Test request exceptions."""

#         mocked.get(
#             f"https://api.getcookidoo.com/rest/v2/cookidoousers/{UUID}",
#             exception=exception,
#         )
#         monkeypatch.setattr(cookidoo, "uuid", UUID)

#         with pytest.raises(CookidooRequestException):
#             await cookidoo.get_user_account()

#     async def test_unauthorized(self, mocked:aioresponses, cookidoo: Cookidoo, monkeypatch):
#         """Test unauthorized exception."""
#         mocked.get(
#             f"https://api.getcookidoo.com/rest/v2/cookidoousers/{UUID}",
#             status=HTTPStatus.UNAUTHORIZED,
#             payload={"error_description": ""},
#         )
#         monkeypatch.setattr(cookidoo, "uuid", UUID)
#         with pytest.raises(CookidooAuthException):
#             await cookidoo.get_user_account()

#     @pytest.mark.parametrize("status", [HTTPStatus.OK, HTTPStatus.UNAUTHORIZED])
#     async def test_parse_exception(self, mocked:aioresponses, cookidoo: Cookidoo, monkeypatch, status):
#         """Test parse exceptions."""
#         mocked.get(
#             f"https://api.getcookidoo.com/rest/v2/cookidoousers/{UUID}",
#             status=status,
#             body="not json",
#             content_type="application/json",
#         )
#         monkeypatch.setattr(cookidoo, "uuid", UUID)

#         with pytest.raises(CookidooParseException):
#             await cookidoo.get_user_account()


# class TestGetAllUserSettings:
#     """Tests for get_all_user_settings method."""

#     async def test_get_all_user_settings(self, cookidoo, mocked, monkeypatch):
#         """Test for get_user_account."""

#         mocked.get(
#             f"https://api.getcookidoo.com/rest/cookidoousersettings/{UUID}",
#             payload=BRING_USER_SETTINGS_RESPONSE,
#             status=HTTPStatus.OK,
#         )

#         monkeypatch.setattr(cookidoo, "uuid", UUID)
#         data = await cookidoo.get_all_user_settings()

#         assert data == BRING_USER_SETTINGS_RESPONSE

#     @pytest.mark.parametrize(
#         "exception",
#         [
#             asyncio.TimeoutError,
#             aiohttp.ClientError,
#         ],
#     )
#     async def test_request_exception(self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception, monkeypatch):
#         """Test request exceptions."""

#         mocked.get(
#             f"https://api.getcookidoo.com/rest/cookidoousersettings/{UUID}",
#             exception=exception,
#         )
#         monkeypatch.setattr(cookidoo, "uuid", UUID)

#         with pytest.raises(CookidooRequestException):
#             await cookidoo.get_all_user_settings()

#     async def test_unauthorized(self, mocked:aioresponses, cookidoo: Cookidoo, monkeypatch):
#         """Test unauthorized exception."""
#         mocked.get(
#             f"https://api.getcookidoo.com/rest/cookidoousersettings/{UUID}",
#             status=HTTPStatus.UNAUTHORIZED,
#             payload={"error_description": ""},
#         )
#         monkeypatch.setattr(cookidoo, "uuid", UUID)
#         with pytest.raises(CookidooAuthException):
#             await cookidoo.get_all_user_settings()

#     @pytest.mark.parametrize("status", [HTTPStatus.OK, HTTPStatus.UNAUTHORIZED])
#     async def test_parse_exception(self, mocked:aioresponses, cookidoo: Cookidoo, monkeypatch, status):
#         """Test parse exceptions."""
#         mocked.get(
#             f"https://api.getcookidoo.com/rest/cookidoousersettings/{UUID}",
#             status=status,
#             body="not json",
#             content_type="application/json",
#         )
#         monkeypatch.setattr(cookidoo, "uuid", UUID)

#         with pytest.raises(CookidooParseException):
#             await cookidoo.get_all_user_settings()

#     async def test_load_user_list_settings(self, cookidoo, monkeypatch):
#         """Test __load_user_list_settings."""

#         async def mocked_get_all_user_settings(self):
#             return BRING_USER_SETTINGS_RESPONSE

#         monkeypatch.setattr(
#             Cookidoo, "get_all_user_settings", mocked_get_all_user_settings
#         )
#         data = await cookidoo._Cookidoo__load_user_list_settings()

#         assert data[UUID]["listArticleLanguage"] == "de-DE"

#     async def test_load_user_list_settings_exception(self, cookidoo, monkeypatch):
#         """Test __load_user_list_settings."""

#         async def mocked_get_all_user_settings(self):
#             raise CookidooRequestException

#         monkeypatch.setattr(
#             Cookidoo, "get_all_user_settings", mocked_get_all_user_settings
#         )

#         with pytest.raises(CookidooTranslationException):
#             await cookidoo._Cookidoo__load_user_list_settings()


# class TestTranslate:
#     """Test for __translate method."""

#     def test_translate_to_locale(self, cookidoo, monkeypatch):
#         """Test __translate with to_locale."""
#         monkeypatch.setattr(
#             cookidoo,
#             "_Cookidoo__translations",
#             {"de-DE": {"Pouletbrüstli": "Hähnchenbrust"}},
#         )

#         item = cookidoo._Cookidoo__translate("Pouletbrüstli", to_locale="de-DE")

#         assert item == "Hähnchenbrust"

#     def test_translate_from_locale(self, cookidoo, monkeypatch):
#         """Test __translate with from_locale."""
#         monkeypatch.setattr(
#             cookidoo,
#             "_Cookidoo__translations",
#             {"de-DE": {"Pouletbrüstli": "Hähnchenbrust"}},
#         )

#         item = cookidoo._Cookidoo__translate("Hähnchenbrust", from_locale="de-DE")

#         assert item == "Pouletbrüstli"

#     def test_translate_value_error_no_locale(self, cookidoo):
#         """Test __translate with missing locale argument."""
#         with pytest.raises(
#             ValueError,
#             match="One of the arguments from_locale or to_locale required.",
#         ):
#             cookidoo._Cookidoo__translate("item_name")

#     def test_translate_value_error_unsupported_locale(self, cookidoo):
#         """Test __translate with unsupported locale."""
#         locale = "en-ES"
#         with pytest.raises(
#             ValueError, match=f"Locale {locale} not supported by Cookidoo."
#         ):
#             cookidoo._Cookidoo__translate("item_name", from_locale=locale)

#     def test_translate_exception(self, cookidoo):
#         """Test __translate CookidooTranslationException."""
#         with pytest.raises(CookidooTranslationException):
#             cookidoo._Cookidoo__translate("item_name", from_locale="de-DE")


# class TestBatchUpdateList:
#     """Tests for batch_update_list."""

#     @pytest.mark.parametrize(
#         ("item", "operation"),
#         [
#             (CookidooItem(itemId="item0", spec="spec", uuid=""), CookidooItemOperation.ADD),
#             (
#                 CookidooItem(itemId="item1", spec="spec", uuid="uuid"),
#                 CookidooItemOperation.COMPLETE,
#             ),
#             (
#                 CookidooItem(itemId="item2", spec="spec", uuid="uuid"),
#                 CookidooItemOperation.REMOVE,
#             ),
#             (
#                 CookidooItem(
#                     itemId="item3",
#                     spec="spec",
#                     uuid="uuid",
#                     operation=CookidooItemOperation.ADD,
#                 ),
#                 None,
#             ),
#             (
#                 CookidooItem(
#                     itemId="item4",
#                     spec="spec",
#                     uuid="uuid",
#                     operation=CookidooItemOperation.COMPLETE,
#                 ),
#                 None,
#             ),
#             (
#                 CookidooItem(
#                     itemId="item5",
#                     spec="spec",
#                     uuid="uuid",
#                     operation=CookidooItemOperation.REMOVE,
#                 ),
#                 None,
#             ),
#             (
#                 CookidooItem(
#                     itemId="item6",
#                     spec="spec",
#                     uuid="uuid",
#                     operation="TO_PURCHASE",
#                 ),
#                 None,
#             ),
#             (
#                 CookidooItem(
#                     itemId="item7",
#                     spec="spec",
#                     uuid="uuid",
#                     operation="TO_RECENTLY",
#                 ),
#                 None,
#             ),
#             (
#                 CookidooItem(
#                     itemId="item8",
#                     spec="spec",
#                     uuid="uuid",
#                     operation="REMOVE",
#                 ),
#                 None,
#             ),
#             (
#                 CookidooItem(
#                     itemId="item9",
#                     spec="spec",
#                     uuid="uuid",
#                 ),
#                 None,
#             ),
#             (
#                 CookidooItem(
#                     itemId="item10",
#                     spec="spec",
#                     uuid="uuid",
#                     operation=CookidooItemOperation.COMPLETE,
#                 ),
#                 CookidooItemOperation.ADD,
#             ),
#             (
#                 CookidooItem(
#                     itemId="item11",
#                     spec="spec",
#                     uuid="uuid",
#                     operation=CookidooItemOperation.REMOVE,
#                 ),
#                 CookidooItemOperation.ADD,
#             ),
#             (
#                 CookidooItem(itemId="item12", spec="", uuid=""),
#                 CookidooItemOperation.ADD,
#             ),
#             (
#                 CookidooItem(itemId="item13", spec="", uuid="uuid"),
#                 CookidooItemOperation.ADD,
#             ),
#             (
#                 CookidooItem(itemId="item14", spec="spec", uuid=""),
#                 CookidooItemOperation.ADD,
#             ),
#             (
#                 CookidooItem(itemId="item15", spec="spec", uuid="uuid"),
#                 CookidooItemOperation.ADD,
#             ),
#             (
#                 {"itemId": "item16", "spec": "spec", "uuid": "uuid"},
#                 CookidooItemOperation.ADD,
#             ),
#         ],
#     )
#     async def test_batch_update_list_single_item(
#         self, cookidoo, mocked, monkeypatch, item, operation
#     ):
#         """Test batch_update_list."""
#         expected = {
#             "changes": [
#                 {
#                     "accuracy": "0.0",
#                     "altitude": "0.0",
#                     "latitude": "0.0",
#                     "longitude": "0.0",
#                     "itemId": item["itemId"],
#                     "spec": item["spec"],
#                     "uuid": item["uuid"],
#                     "operation": str(
#                         item.get("operation", operation or CookidooItemOperation.ADD)
#                     ),
#                 }
#             ],
#             "sender": "",
#         }
#         mocked.put(
#             url := f"https://api.getcookidoo.com/rest/v2/cookidoolists/{UUID}/items",
#             status=HTTPStatus.OK,
#         )
#         monkeypatch.setattr(Cookidoo, "_Cookidoo__locale", lambda _, x: "de-DE")
#         monkeypatch.setattr(Cookidoo, "_Cookidoo__translate", mocked_translate)

#         if operation:
#             r = await cookidoo.batch_update_list(UUID, item, operation)
#         else:
#             r = await cookidoo.batch_update_list(UUID, item)
#         assert r.status == HTTPStatus.OK
#         mocked.assert_called_with(
#             url,
#             method="PUT",
#             headers=DEFAULT_HEADERS,
#             data=None,
#             json=expected,
#         )

#     async def test_batch_update_list_multiple_items(
#         self, cookidoo, mocked, monkeypatch
#     ):
#         """Test batch_update_list."""
#         test_items = [
#             CookidooItem(
#                 itemId="item1",
#                 spec="spec1",
#                 uuid="uuid1",
#                 operation=CookidooItemOperation.ADD,
#             ),
#             CookidooItem(
#                 itemId="item2",
#                 spec="spec2",
#                 uuid="uuid2",
#                 operation=CookidooItemOperation.COMPLETE,
#             ),
#             CookidooItem(
#                 itemId="item3",
#                 spec="spec3",
#                 uuid="uuid3",
#                 operation=CookidooItemOperation.REMOVE,
#             ),
#         ]

#         expected = {
#             "changes": [
#                 {
#                     "accuracy": "0.0",
#                     "altitude": "0.0",
#                     "latitude": "0.0",
#                     "longitude": "0.0",
#                     "itemId": "item1",
#                     "spec": "spec1",
#                     "uuid": "uuid1",
#                     "operation": "TO_PURCHASE",
#                 },
#                 {
#                     "accuracy": "0.0",
#                     "altitude": "0.0",
#                     "latitude": "0.0",
#                     "longitude": "0.0",
#                     "itemId": "item2",
#                     "spec": "spec2",
#                     "uuid": "uuid2",
#                     "operation": "TO_RECENTLY",
#                 },
#                 {
#                     "accuracy": "0.0",
#                     "altitude": "0.0",
#                     "latitude": "0.0",
#                     "longitude": "0.0",
#                     "itemId": "item3",
#                     "spec": "spec3",
#                     "uuid": "uuid3",
#                     "operation": "REMOVE",
#                 },
#             ],
#             "sender": "",
#         }
#         mocked.put(
#             url := f"https://api.getcookidoo.com/rest/v2/cookidoolists/{UUID}/items",
#             status=HTTPStatus.OK,
#         )
#         monkeypatch.setattr(Cookidoo, "_Cookidoo__locale", lambda _, x: "de-DE")
#         monkeypatch.setattr(Cookidoo, "_Cookidoo__translate", mocked_translate)

#         r = await cookidoo.batch_update_list(UUID, test_items)

#         assert r.status == HTTPStatus.OK
#         mocked.assert_called_with(
#             url,
#             method="PUT",
#             headers=DEFAULT_HEADERS,
#             data=None,
#             json=expected,
#         )

#     @pytest.mark.parametrize(
#         "exception",
#         [
#             asyncio.TimeoutError,
#             aiohttp.ClientError,
#         ],
#     )
#     async def test_request_exception(self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception):
#         """Test request exceptions."""

#         mocked.put(
#             f"https://api.getcookidoo.com/rest/v2/cookidoolists/{UUID}/items",
#             exception=exception,
#         )

#         with pytest.raises(CookidooRequestException):
#             await cookidoo.batch_update_list(
#                 UUID, CookidooItem(itemId="item_name", spec="spec", uuid=UUID)
#             )

#     async def test_unauthorized(self, mocked:aioresponses, cookidoo: Cookidoo, monkeypatch):
#         """Test unauthorized exception."""
#         mocked.put(
#             f"https://api.getcookidoo.com/rest/v2/cookidoolists/{UUID}/items",
#             status=HTTPStatus.UNAUTHORIZED,
#             payload={"error_description": ""},
#         )

#         with pytest.raises(CookidooAuthException):
#             await cookidoo.batch_update_list(
#                 UUID, CookidooItem(itemId="item_name", spec="spec", uuid=UUID)
#             )

#     async def test_parse_exception(self, mocked:aioresponses, cookidoo: Cookidoo, monkeypatch):
#         """Test parse exceptions."""
#         mocked.put(
#             f"https://api.getcookidoo.com/rest/v2/cookidoolists/{UUID}/items",
#             status=HTTPStatus.UNAUTHORIZED,
#             body="not json",
#             content_type="application/json",
#         )

#         with pytest.raises(CookidooParseException):
#             await cookidoo.batch_update_list(
#                 UUID, CookidooItem(itemId="item_name", spec="spec", uuid=UUID)
#             )


# class TestRetrieveNewAccessToken:
#     """Test for retrieve_new_access_token method."""

#     async def test_retrieve_new_access_token(self, mocked:aioresponses, cookidoo: Cookidoo, monkeypatch):
#         """Test retrieve_new_access_token."""
#         mocked.post(
#             "https://api.getcookidoo.com/rest/v2/cookidooauth/token",
#             status=HTTPStatus.OK,
#             payload=BRING_TOKEN_RESPONSE,
#         )
#         monkeypatch.setattr(cookidoo, "refresh_token", "test_refresh_token")
#         monkeypatch.setattr(time, "time", lambda: 0)
#         data = await cookidoo.retrieve_new_access_token()

#         assert data == BRING_TOKEN_RESPONSE
#         assert cookidoo.headers["Authorization"] == "Bearer {access_token}"
#         assert cookidoo.expires_in == BRING_TOKEN_RESPONSE["expires_in"]

#     @pytest.mark.parametrize(
#         "exception",
#         [
#             asyncio.TimeoutError,
#             aiohttp.ClientError,
#         ],
#     )
#     async def test_request_exception(self, mocked: aioresponses, cookidoo: Cookidoo, exception: Exception):
#         """Test request exceptions."""

#         mocked.post(
#             "https://api.getcookidoo.com/rest/v2/cookidooauth/token",
#             exception=exception,
#         )

#         with pytest.raises(CookidooRequestException):
#             await cookidoo.retrieve_new_access_token()

#     async def test_auth_exception(self, mocked:aioresponses, cookidoo: Cookidoo):
#         """Test request exceptions."""

#         mocked.post(
#             "https://api.getcookidoo.com/rest/v2/cookidooauth/token",
#             status=HTTPStatus.UNAUTHORIZED,
#             payload={"error_description": ""},
#         )

#         with pytest.raises(CookidooAuthException):
#             await cookidoo.retrieve_new_access_token()

#     @pytest.mark.parametrize("status", [HTTPStatus.OK, HTTPStatus.UNAUTHORIZED])
#     async def test_parse_exception(self, mocked: aioresponses, cookidoo: Cookidoo, status: HTTPStatus):
#         """Test request exceptions."""

#         mocked.post(
#             "https://api.getcookidoo.com/rest/v2/cookidooauth/token",
#             status=status,
#             body="not json",
#             content_type="application/json",
#         )

#         with pytest.raises(CookidooParseException):
#             await cookidoo.retrieve_new_access_token()


# class TestSetListArticleLanguage:
#     """Tests for set_list_article_language method."""

#     async def test_set_list_article_language(self, mocked:aioresponses, cookidoo: Cookidoo, monkeypatch):
#         """Test set list article language."""
#         mocked.post(
#             f"https://api.getcookidoo.com/rest/cookidoousersettings/{UUID}/{UUID}/listArticleLanguage",
#             status=HTTPStatus.OK,
#         )

#         monkeypatch.setattr(cookidoo, "uuid", UUID)

#         async def mocked__load_user_list_settings(*args, **kwargs):
#             """Mock __load_user_list_settings."""
#             return {UUID: {"listArticleLanguage": "de-DE"}}

#         monkeypatch.setattr(
#             Cookidoo, "_Cookidoo__load_user_list_settings", mocked__load_user_list_settings
#         )

#         resp = await cookidoo.set_list_article_language(UUID, "de-DE")
#         assert resp.status == HTTPStatus.OK

#     @pytest.mark.parametrize(
#         "exception",
#         [
#             asyncio.TimeoutError,
#             aiohttp.ClientError,
#         ],
#     )
#     async def test_request_exception(self, mocked:aioresponses, cookidoo: Cookidoo, monkeypatch, exception):
#         """Test request exceptions."""

#         mocked.post(
#             f"https://api.getcookidoo.com/rest/cookidoousersettings/{UUID}/{UUID}/listArticleLanguage",
#             exception=exception,
#         )

#         monkeypatch.setattr(cookidoo, "uuid", UUID)

#         with pytest.raises(CookidooRequestException):
#             await cookidoo.set_list_article_language(UUID, "de-DE")

#     async def test_unauthorized(self, mocked:aioresponses, cookidoo: Cookidoo, monkeypatch):
#         """Test unauthorized exception."""
#         mocked.post(
#             f"https://api.getcookidoo.com/rest/cookidoousersettings/{UUID}/{UUID}/listArticleLanguage",
#             status=HTTPStatus.UNAUTHORIZED,
#         )
#         monkeypatch.setattr(cookidoo, "uuid", UUID)
#         with pytest.raises(CookidooAuthException):
#             await cookidoo.set_list_article_language(UUID, "de-DE")

#     async def test_value_error(self, cookidoo):
#         """Test ValueError exception."""

#         with pytest.raises(ValueError):
#             await cookidoo.set_list_article_language(UUID, "es-CO")
