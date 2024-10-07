"""Cookidoo API types."""

from typing import Literal, TypedDict

CookidooBrowserType = Literal["chromium", "firefox", "webkit"]
"""Cookidoo browser type"""

CookidooCaptchaRecoveryType = Literal["fail", "user_input", "capsolver"]
"""Cookidoo captcha recovery type"""

CookidooItemStateType = Literal["pending", "checked"]
"""Cookidoo item state type"""

CookidooWaiterStateType = Literal["attached", "detached", "hidden", "visible"]


class CookidooConfig(TypedDict):
    """Cookidoo config type.

    Attributes
    ----------
    language_code
        The language code to use for the api
    browser
        The browser to use
    remote_addr
        If not set, local browser are used, otherwise use the remote addr as runner
    remote_port
        Set the port to connect to on the remote addr
    headless
        Switch between headless and headful mode

    email
        The email to login
    password
        The password to login

    network_timeout
        Duration to wait before considering a navigation as failed
    timeout
        Duration to wait before any action (selector, click, etc.) as failed
    retries
        Retry a complex actions N times before considering it as failed

    tracing
        Trace all action happening and save it as trace.zip to review
    screenshots
        Make screenshots at important moments
    out_dir
        Where all the tracing and screenshots are exported to

    """

    language_code: str
    browser: CookidooBrowserType
    remote_addr: str | None
    remote_port: str | None
    headless: bool

    email: str
    password: str

    network_timeout: int
    timeout: int
    retries: int

    tracing: bool
    screenshots: bool
    out_dir: str


class CookidooItem(TypedDict):
    """Cookidoo item type.

    Attributes
    ----------
    id
        The id of the item
    label
        The label of the item
    description
        The description of the item, including the quantity or other helpful information
    state
        The state of the item

    """

    id: str
    label: str
    description: str | None
    state: CookidooItemStateType
