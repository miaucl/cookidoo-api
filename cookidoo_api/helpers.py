"""Helpers for the Cookidoo API."""

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


def token_header_constructor(token: str) -> dict[str, str]:
    """Construct a token header.

    The `token_cookie_constructor` is usually preferred to set tokens. This can still be used in some cases, but be aware, Chrome is a bit picky and likes to overwrite them sometimes.

    Example:
    ```python
    context = await browser.new_context(
        extra_http_headers=token_header_constructor(token)
    )
    ```

    Parameters
    ----------
    token
        The token to put into the header

    Returns
    -------
    dict
        A dict with header values

    """
    return {"Cookie": f"v-token={token}"}


def token_cookie_constructor(token: str) -> Cookie:
    """Construct a token cookie.

    This lets one add cookie data to the current session. Beware, you first need to open a page and let the browser set up the session, otherwise it does not work.

    Example:
    ```python
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto("<some page>")
    await context.add_cookies([<your cookie>])
    # now every subsequent request contains the cookie
    ```

    Parameters
    ----------
    token
        The token to put into the header

    Returns
    -------
    Cookie
        A dict with header values

    """
    return Cookie(
        {
            "name": "v-token",
            "value": token,
            "domain": "cookidoo.ch",
            "path": "/",
            "httpOnly": True,
            "secure": True,
            "sameSite": "Strict",
        }
    )


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
