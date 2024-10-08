"""Helpers for the Cookidoo API."""

from datetime import UTC, datetime
import json
import re
import socket
from typing import cast

from playwright.async_api import Cookie

ipv4_pattern = re.compile(r"^(\d{1,3}\.){3}\d{1,3}$")


def cookies_serialize(cookies: list[Cookie]) -> str:
    """Serialize all cookies from the login session to a string for persistency.

    Parameters
    ----------
    cookies
        The cookies in the session to persist

    str
        The serialized data to persist

    """
    return json.dumps(cookies)


def cookies_deserialize(cookies: str) -> list[Cookie]:
    """Deserialize all cookies from the login session from a persisted string.

    Parameters
    ----------
    cookies
        The persisted session cookies as string

    Returns
    -------
    list[Cookie]
        The session cookies

    """
    return cast(list[Cookie], json.loads(cookies))


def merge_cookies(old_cookies: list[Cookie], new_cookies: list[Cookie]) -> list[Cookie]:
    """Merge old an new cookies, avoiding removing other cookies also present.

    Parameters
    ----------
    old_cookies
        The old cookies already persisted
    new_cookies
        The new cookies to persist

    Returns
    -------
    list[Cookie]
        The merged list of the cookies

    """
    cookies = new_cookies[:]
    # Look at all old cookies NOT present in the new cookies and append to the list
    for old_cookie in old_cookies:
        if not next(
            (
                cookie
                for cookie in cookies
                if cookie.get("name") == old_cookie.get("name")
            ),
            None,
        ):
            cookies.append(old_cookie)
    return cookies


def error_message_selector(page: str, selector: str | list[str]) -> str:
    """Create an error message for an unmet selector on a page.

    Parameters
    ----------
    page
        The page of where the selector should appear
    selector
        The selector or list of selectors which was not found

    """
    return f"Selector not found in page.\n\tPage: {page}\n\tSelector:\n\t\t{selector if isinstance(selector, str) else '\n\t\t'.join(selector)}"


def resolve_remote_addr(addr: str) -> str:
    """Resolve the remote address, be it localhost, an IP or a DNS.

    Parameters
    ----------
    addr
        The value to resolve, localhost, IP or DNS

    Returns
    -------
    str
        The IP (or localhost)

    Raises
    ------
    socket.gaierror
        If the DNS could not be resolved due

    """
    try:
        return (
            addr
            if addr == "localhost" or ipv4_pattern.match(addr)
            else socket.gethostbyname(addr)
        )
    except socket.gaierror as e:
        return f"Error resolving {addr}: {e}"


def timestamped_out_dir(out_dir: str) -> str:
    """Create a unique timestamped out dir."""
    return f"{out_dir}/{int(datetime.now(UTC).timestamp())}"
