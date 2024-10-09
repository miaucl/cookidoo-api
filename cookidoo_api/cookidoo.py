"""Cookidoo api implementation."""

import logging

from playwright.async_api import (
    Cookie,
    Error as PlaywrightError,
    TimeoutError as PlaywrightTimeoutError,
    async_playwright,
)

from cookidoo_api.actions import clicker, selector
from cookidoo_api.const import (
    COOKIE_VALIDATION_SELECTOR,
    COOKIE_VALIDATION_URL,
    DEFAULT_COOKIDOO_CONFIG,
    LOGIN_CAPTCHA_SELECTOR,
    LOGIN_EMAIL_SELECTOR,
    LOGIN_ERROR_NOTIFICATION_SELECTOR,
    LOGIN_PASSWORD_SELECTOR,
    LOGIN_START_SELECTOR,
    LOGIN_START_URL,
    LOGIN_SUBMIT_SELECTOR,
)
from cookidoo_api.exceptions import (
    CookidooActionException,
    CookidooAuthBotDetectionException,
    CookidooAuthException,
    CookidooSelectorException,
)
from cookidoo_api.helpers import (
    cookies_deserialize,
    cookies_serialize,
    error_message_selector,
    merge_cookies,
    timestamped_out_dir,
)
from cookidoo_api.jobs import (
    CookidooBrowser,
    LandingPage,
    ShoppingList,
    add_items,
    clear_items,
    create_additional_items,
    delete_additional_items,
    get_additional_items,
    get_items,
    remove_items,
    update_additional_items,
    update_items,
)
from cookidoo_api.types import CookidooCaptchaRecoveryType, CookidooConfig, CookidooItem

_LOGGER = logging.getLogger(__name__)


class Cookidoo:
    """Unofficial Cookidoo API interface.

    Attributes
    ----------
    _cfg
        Cookidoo config
    _cookies
        The cookies from the login

    """

    _cfg: CookidooConfig
    _cookies: list[Cookie]

    def __init__(
        self, cfg: CookidooConfig = DEFAULT_COOKIDOO_CONFIG, cookies: str = ""
    ) -> None:
        """Init function for Bring API.

        Parameters
        ----------
        cfg
            Cookidoo config
        cookies
            Session cookies that already exist


        """
        self._cfg = cfg
        self._cookies = cookies_deserialize(cookies) if cookies else []

    @property
    def cookies(self) -> str:
        """Getter for the cookies."""
        return cookies_serialize(self._cookies)

    @cookies.setter
    def cookies(self, value: str) -> None:
        """Setter for the cookies."""
        self._cookies = cookies_deserialize(value)

    async def validate_cookies(self, out_dir: str = "out/validation") -> None:
        """Validate the cookies.

        Parameters
        ----------
        out_dir
            Get directory to store output such as trace or screenshots

        Raises
        ------
        CookidooAuthException
            When the cookies are not valid anymore

        """
        _out_dir = timestamped_out_dir(out_dir)

        async with (
            async_playwright() as p,
            CookidooBrowser(self._cfg, p) as browser,
            LandingPage(self._cfg, browser, self._cookies, _out_dir) as page,
        ):
            try:
                # Go to account page
                await page.goto(COOKIE_VALIDATION_URL)

                # Take a screenshot of the account page
                if self._cfg["screenshots"]:
                    await page.screenshot(path=f"{_out_dir}/1-cookie-validation.png")

                # Await the welcome message
                try:
                    await page.wait_for_selector(COOKIE_VALIDATION_SELECTOR)
                except PlaywrightTimeoutError as e:
                    raise CookidooSelectorException(
                        f"Welcome message not found due to a timeout.\n{error_message_selector(page.url, COOKIE_VALIDATION_SELECTOR)}"
                    ) from e
                _LOGGER.debug("Successful validation of the cookies")
                cookies = await page.context.cookies()
                if _LOGGER.level <= logging.DEBUG:
                    old_session_cookie = next(
                        (
                            cookie
                            for cookie in self._cookies
                            if cookie.get("name") == "session"
                        ),
                        None,
                    )
                    new_session_cookie = next(
                        (
                            cookie
                            for cookie in cookies
                            if cookie.get("name") == "session"
                        ),
                        None,
                    )
                    old_token_cookie = next(
                        (
                            cookie
                            for cookie in self._cookies
                            if cookie.get("name") == "v-token"
                        ),
                        None,
                    )
                    new_token_cookie = next(
                        (
                            cookie
                            for cookie in cookies
                            if cookie.get("name") == "v-token"
                        ),
                        None,
                    )
                    old_auth_cookie = next(
                        (
                            cookie
                            for cookie in self._cookies
                            if cookie.get("name") == "v-authenticated"
                        ),
                        None,
                    )
                    new_auth_cookie = next(
                        (
                            cookie
                            for cookie in cookies
                            if cookie.get("name") == "v-authenticated"
                        ),
                        None,
                    )
                    if (
                        not new_session_cookie
                        or not new_token_cookie
                        or not new_auth_cookie
                    ):
                        _LOGGER.debug(
                            "New session does not contain all expected cookies: %s",
                            cookies,
                        )
                    else:
                        if not old_session_cookie or old_session_cookie.get(
                            "name"
                        ) != new_session_cookie.get("name"):
                            _LOGGER.debug("New 'session' cookie available")
                        if not old_token_cookie or old_token_cookie.get(
                            "name"
                        ) != new_token_cookie.get("name"):
                            _LOGGER.debug("New 'token' cookie available")
                        if not old_auth_cookie or old_auth_cookie.get(
                            "name"
                        ) != new_auth_cookie.get("name"):
                            _LOGGER.debug("New 'auth' cookie available")
                self._cookies = merge_cookies(self._cookies, cookies)
            except CookidooSelectorException as e:
                raise CookidooAuthException("Cookies are not valid.") from e

    async def login(
        self,
        captcha_recovery_mode: CookidooCaptchaRecoveryType = "fail",
        force_session_refresh: bool = False,
        out_dir: str = "out/login",
    ) -> None:
        """Login to the cookidoo website and store the cookies. Also functions to refresh the session.

        Parameters
        ----------
        self
            Cookidoo class
        captcha_recovery_mode
            Captcha recovery is useful when you have been detected as a bot or automation script. It lets you use one of the following strategies:
            - fail: Do nothing and fail (default)
            - user_input: Wait indefinitely for the user to solve the captcha (only viable for non-headless setups)
            - capsolver: Using capsolver to solve the captcha (tbd)
        force_session_refresh
            Force the token refresh and skip cookie validation
        out_dir
            The directory to store output such as trace or screenshots

        Raises
        ------
        CookidooSelectorException
            When the page does not behave as expected and some content is not available
        CookidooActionException
            When the page does not allow to perform an expected action
        CookidooAuthBotDetectionException
            When a captcha has been detected and is blocking the login process
        CookidooAuthException
            Bad username or password

        """
        _out_dir = timestamped_out_dir(out_dir)

        # Check cookies and short circuit
        if self._cookies and not force_session_refresh:
            try:
                await self.validate_cookies()
            except CookidooAuthException as e:
                _LOGGER.warning(
                    "Cached token could not be validated, proceeding with login process: %s",
                    str(e),
                )
            else:
                return

        async with (
            async_playwright() as p,
            CookidooBrowser(self._cfg, p) as browser,
            LandingPage(self._cfg, browser, self._cookies, _out_dir) as page,
        ):
            try:
                _LOGGER.debug("Attempt login")

                # Go to login start page
                await page.goto(LOGIN_START_URL)

                # Take a screenshot of the login start page
                if self._cfg["screenshots"]:
                    await page.screenshot(path=f"{_out_dir}/1-login-start.png")

                # Await the button and click on "Login"
                login_el = await selector(page, LOGIN_START_SELECTOR)
                await clicker(page, login_el, "Cannot not click on login")

                # Take a screenshot of the login details page
                if self._cfg["screenshots"]:
                    await page.screenshot(path=f"{_out_dir}/2-login-details.png")

                # Await the email field and enter email and password
                try:
                    # If captcha recovery mode is user_input, wait here until captcha is solved
                    if captcha_recovery_mode == "user_input":
                        if not self._cfg["headless"]:
                            _LOGGER.fatal(
                                "Using captcha_recovery_mode='user_input' is not supported for headless runners. Process is blocked, manual abort required!"
                            )
                        await page.wait_for_selector(
                            LOGIN_EMAIL_SELECTOR, timeout=1000000
                        )
                    elif captcha_recovery_mode == "capsolver":
                        if not self._cfg["headless"]:
                            _LOGGER.warning(
                                "Capsolver is not yet implemented. Should you have the capsolver browser extension installed, ignore this warning."
                            )
                        await page.wait_for_selector(
                            LOGIN_EMAIL_SELECTOR, timeout=1000000
                        )
                    # Assume, login should success normally
                    else:
                        await page.wait_for_selector(LOGIN_EMAIL_SELECTOR)
                except PlaywrightTimeoutError as e:
                    login_error_reason = "generic"
                    try:
                        await page.wait_for_selector(LOGIN_CAPTCHA_SELECTOR)
                        # Captcha against bot detection...
                        login_error_reason = "captcha"
                    except Exception as _e:
                        # It is not a captcha
                        pass

                    if login_error_reason == "captcha":
                        raise CookidooAuthBotDetectionException(
                            "Cannot login due to captcha."
                        ) from e
                    else:
                        raise CookidooSelectorException(
                            f"Email field not found due to a timeout.\n{error_message_selector(page.url, LOGIN_EMAIL_SELECTOR)}"
                        ) from e
                try:
                    await page.fill(LOGIN_EMAIL_SELECTOR, self._cfg["email"])
                    await page.fill(LOGIN_PASSWORD_SELECTOR, self._cfg["password"])
                except PlaywrightError as e:
                    raise CookidooSelectorException(
                        f"Email or password field not found.\n{error_message_selector(page.url, LOGIN_EMAIL_SELECTOR)}"
                    ) from e
                except ValueError as e:
                    raise CookidooSelectorException(
                        f"Email or password field do not contain strings.\nEmail: {type(self._cfg['email'])}\nPassword: {type(self._cfg['password'])}"
                    ) from e

                # Take a screenshot of the login details page filled
                if self._cfg["screenshots"]:
                    await page.screenshot(path=f"{_out_dir}/3-login-details-filled.png")

                submit_el = await selector(page, LOGIN_SUBMIT_SELECTOR)
                await clicker(page, submit_el, "Cannot not click on submit")

                cookies = await page.context.cookies()

                for cookie in cookies:
                    if (
                        cookie.get("name") == "v-token"
                        and cookie.get("value")
                        and cookie.get("expires")
                    ):
                        val = cookie.get("value")
                        exp = cookie.get("expires")
                        assert val, "Value for cookie not set"
                        assert exp, "Expiration for cookie not set"
                        _LOGGER.info(
                            "Session cookie 'v-token' found, consider login successful!"
                        )
                        break
                # If no v-token available, login must have failed, looking for reason
                else:
                    try:
                        await page.wait_for_selector(LOGIN_EMAIL_SELECTOR, timeout=500)
                        await page.wait_for_selector(
                            LOGIN_ERROR_NOTIFICATION_SELECTOR, timeout=500
                        )
                        element = await page.query_selector(
                            LOGIN_ERROR_NOTIFICATION_SELECTOR
                        )
                        text_content = (
                            await element.text_content()
                            if element
                            else "Element not found"
                        )
                    except Exception as _e:
                        # It is not a bad login
                        pass
                    else:
                        # Wrong username or password...
                        raise CookidooAuthException(
                            f"Bad username or password.\nNotification displayed: {text_content}"
                        )

                self._cookies = merge_cookies(self._cookies, cookies)

            except CookidooActionException as e:
                raise CookidooAuthException(
                    "Could not get auth token as the login process failed."
                ) from e
            except CookidooSelectorException as e:
                raise CookidooAuthException(
                    "Could not get auth token as the login process failed."
                ) from e

    async def get_items(
        self,
        pending: bool = False,
        checked: bool = False,
        out_dir: str = "out/get_items",
    ) -> list[CookidooItem]:
        """Get items.

        Parameters
        ----------
        cfg
            Cookidoo config
        pending
            Get the pending items
        checked
            Get the checked items
        out_dir
            Get directory to store output such as trace or screenshots

        Returns
        -------
        list[CookidooItem]
            The list of the items

        Raises
        ------
        CookidooAuthException
            When the cookies are not valid anymore
        CookidooSelectorException
            When the page does not behave as expected and some content is not available

        """
        await self.validate_cookies()

        _out_dir = timestamped_out_dir(out_dir)
        async with (
            async_playwright() as p,
            CookidooBrowser(self._cfg, p) as browser,
            LandingPage(self._cfg, browser, self._cookies, _out_dir) as landing_page,
            ShoppingList(self._cfg, landing_page, _out_dir) as page,
        ):
            return await get_items(self._cfg, page, _out_dir, pending, checked)

    async def update_items(
        self,
        items: list[CookidooItem],
        out_dir: str = "out/update_items",
    ) -> list[CookidooItem]:
        """Update items.

        Parameters
        ----------
        cfg
            Cookidoo config
        items
            Get items to update, only the state can be changed
        out_dir
            Get directory to store output such as trace or screenshots

        Returns
        -------
        list[CookidooItem]
            The list of the items

        Raises
        ------
        CookidooAuthException
            When the cookies are not valid anymore
        CookidooSelectorException
            When the page does not behave as expected and some content is not available
        CookidooActionException
            When the page does not allow to perform an expected action
        CookidooUnexpectedStateException
            When something should be changes such as the state, but it is already in that state

        """
        await self.validate_cookies()

        _out_dir = timestamped_out_dir(out_dir)
        async with (
            async_playwright() as p,
            CookidooBrowser(self._cfg, p) as browser,
            LandingPage(self._cfg, browser, self._cookies, _out_dir) as landing_page,
            ShoppingList(self._cfg, landing_page, _out_dir) as page,
        ):
            return await update_items(self._cfg, page, _out_dir, items)

    async def add_items(
        self,
        recipe_id: str,
        out_dir: str = "out/add_items",
    ) -> None:
        """Add items to list from recipe.

        Parameters
        ----------
        cfg
            Cookidoo config
        recipe_id
            The id of the recipe to add the items to the shopping list
        out_dir
            Get directory to store output such as trace or screenshots

        Raises
        ------
        CookidooAuthException
            When the cookies are not valid anymore
        CookidooNavigationException
            When the page could not be found
        CookidooSelectorException
            When the page does not behave as expected and some content is not available
        CookidooActionException
            When the page does not allow to perform an expected action

        """
        await self.validate_cookies()

        _out_dir = timestamped_out_dir(out_dir)
        async with (
            async_playwright() as p,
            CookidooBrowser(self._cfg, p) as browser,
            LandingPage(self._cfg, browser, self._cookies, _out_dir) as page,
        ):
            return await add_items(self._cfg, page, recipe_id, _out_dir)

    async def remove_items(
        self,
        recipe_id: str,
        out_dir: str = "out/remove_items",
    ) -> None:
        """Remove items from list of recipe.

        Parameters
        ----------
        cfg
            Cookidoo config
        recipe_id
            The id of the recipe to remove the items from the shopping list
        out_dir
            Get directory to store output such as trace or screenshots

        Raises
        ------
        CookidooAuthException
            When the cookies are not valid anymore
        CookidooSelectorException
            When the page does not behave as expected and some content is not available
        CookidooActionException
            When the page does not allow to perform an expected action

        """
        await self.validate_cookies()

        _out_dir = timestamped_out_dir(out_dir)
        async with (
            async_playwright() as p,
            CookidooBrowser(self._cfg, p) as browser,
            LandingPage(self._cfg, browser, self._cookies, _out_dir) as landing_page,
            ShoppingList(self._cfg, landing_page, _out_dir) as page,
        ):
            return await remove_items(self._cfg, page, recipe_id, _out_dir)

    async def get_additional_items(
        self,
        pending: bool = False,
        checked: bool = False,
        out_dir: str = "out/get_additional_items",
    ) -> list[CookidooItem]:
        """Get additional items.

        Parameters
        ----------
        cfg
            Cookidoo config
        pending
            Get the pending items
        checked
            Get the checked items
        out_dir
            Get directory to store output such as trace or screenshots

        Returns
        -------
        list[CookidooItem]
            The list of the additional items

        Raises
        ------
        CookidooAuthException
            When the cookies are not valid anymore
        CookidooSelectorException
            When the page does not behave as expected and some content is not available

        """
        await self.validate_cookies()

        _out_dir = timestamped_out_dir(out_dir)
        async with (
            async_playwright() as p,
            CookidooBrowser(self._cfg, p) as browser,
            LandingPage(self._cfg, browser, self._cookies, _out_dir) as landing_page,
            ShoppingList(self._cfg, landing_page, _out_dir) as page,
        ):
            return await get_additional_items(
                self._cfg, page, _out_dir, pending, checked
            )

    async def update_additional_items(
        self,
        additional_items: list[CookidooItem],
        out_dir: str = "out/update_additional_items",
    ) -> list[CookidooItem]:
        """Update additional items.

        Parameters
        ----------
        cfg
            Cookidoo config
        additional_items
            The additional items to update, only the state and label can be changed
        out_dir
            Get directory to store output such as trace or screenshots

        Returns
        -------
        list[CookidooItem]
            The list of the additional items

        Raises
        ------
        CookidooAuthException
            When the cookies are not valid anymore
        CookidooSelectorException
            When the page does not behave as expected and some content is not available
        CookidooActionException
            When the page does not allow to perform an expected action
        CookidooUnexpectedStateException
            When something should be changes such as the state, but it is already in that state

        """
        await self.validate_cookies()

        _out_dir = timestamped_out_dir(out_dir)
        async with (
            async_playwright() as p,
            CookidooBrowser(self._cfg, p) as browser,
            LandingPage(self._cfg, browser, self._cookies, _out_dir) as landing_page,
            ShoppingList(self._cfg, landing_page, _out_dir) as page,
        ):
            return await update_additional_items(
                self._cfg, page, _out_dir, additional_items
            )

    async def create_additional_items(
        self,
        additional_item_labels: list[str],
        out_dir: str = "out/create_additional_items",
    ) -> list[CookidooItem]:
        """Create additional items.

        Parameters
        ----------
        cfg
            Cookidoo config
        additional_item_labels
            The additional item labels to create, only the label can be set, as the default state `pending` is forced (chain with immediate update call for work-around)
        out_dir
            Get directory to store output such as trace or screenshots

        Returns
        -------
        list[CookidooItem]
            The list of the additional items

        Raises
        ------
        CookidooAuthException
            When the cookies are not valid anymore
        CookidooSelectorException
            When the page does not behave as expected and some content is not available
        CookidooActionException
            When the page does not allow to perform an expected action
        CookidooUnexpectedStateException
            When something should be changes such as the state, but it is already in that state

        """
        await self.validate_cookies()

        _out_dir = timestamped_out_dir(out_dir)
        async with (
            async_playwright() as p,
            CookidooBrowser(self._cfg, p) as browser,
            LandingPage(self._cfg, browser, self._cookies, _out_dir) as landing_page,
            ShoppingList(self._cfg, landing_page, _out_dir) as page,
        ):
            return await create_additional_items(
                self._cfg,
                page,
                _out_dir,
                [
                    CookidooItem(
                        {
                            "id": "",  # Will be set in the job
                            "label": label,
                            "state": "pending",  # Forced default state for new additional items
                            "description": "",  # NA for additional items
                        }
                    )
                    for label in additional_item_labels
                ],
            )

    async def delete_additional_items(
        self,
        additional_items: list[CookidooItem] | list[str],
        out_dir: str = "out/delete_additional_items",
    ) -> None:
        """Delete additional items.

        Parameters
        ----------
        cfg
            Cookidoo config
        additional_items
            The additional items to delete, only the id is required
        out_dir
            Get directory to store output such as trace or screenshots

        Raises
        ------
        CookidooAuthException
            When the cookies are not valid anymore
        CookidooSelectorException
            When the page does not behave as expected and some content is not available
        CookidooActionException
            When the page does not allow to perform an expected action
        CookidooUnexpectedStateException
            When something should be changes such as the state, but it is already in that state

        """
        await self.validate_cookies()

        _out_dir = timestamped_out_dir(out_dir)
        async with (
            async_playwright() as p,
            CookidooBrowser(self._cfg, p) as browser,
            LandingPage(self._cfg, browser, self._cookies, _out_dir) as landing_page,
            ShoppingList(self._cfg, landing_page, _out_dir) as page,
        ):
            await delete_additional_items(
                self._cfg,
                page,
                _out_dir,
                additional_items,
            )

    async def clear_items(
        self,
        out_dir: str = "out/clear_items",
    ) -> None:
        """Clear items from list.

        This a destructive operation and cannot be undone. This remove all items, regardless of item state.

        Parameters
        ----------
        cfg
            Cookidoo config
        out_dir
            Get directory to store output such as trace or screenshots

        Raises
        ------
        CookidooAuthException
            When the cookies are not valid anymore
        CookidooSelectorException
            When the page does not behave as expected and some content is not available
        CookidooActionException
            When the page does not allow to perform an expected action

        """
        await self.validate_cookies()

        _out_dir = timestamped_out_dir(out_dir)
        async with (
            async_playwright() as p,
            CookidooBrowser(self._cfg, p) as browser,
            LandingPage(self._cfg, browser, self._cookies, _out_dir) as landing_page,
            ShoppingList(self._cfg, landing_page, _out_dir) as page,
        ):
            return await clear_items(self._cfg, page, _out_dir)
