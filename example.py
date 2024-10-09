#!/usr/bin/env python3
"""Example script for cookidoo-api."""

import asyncio
import logging
import os
import sys

from dotenv import load_dotenv

from cookidoo_api import DEFAULT_COOKIDOO_CONFIG, Cookidoo

load_dotenv()

# Configure the root logger
logging.basicConfig(
    level=logging.DEBUG,  # Set the logging level (DEBUG, INFO, WARNING, etc.)
    format="%(asctime)s [%(levelname)8s] %(name)s:%(lineno)s %(message)s",  # Format of the log messages
    handlers=[  # Specify the handlers for the logger
        logging.StreamHandler(sys.stdout)  # Output to stdout
    ],
)


def save_cookies(cookies: str):
    """Save cookies to file."""
    with open(".cookies", "w") as file:
        file.write(cookies)


async def main():
    """Run main function."""
    cookies = ""
    if os.path.exists(".cookies"):
        # Open and read the file
        with open(".cookies") as file:
            cookies = file.read()

    cookidoo = Cookidoo(
        {
            **DEFAULT_COOKIDOO_CONFIG,
            # Choose a local runner
            "browser": "chromium",
            "headless": True,
            # Choose a remote runner instead
            # "remote_addr": "my.server.local",
            # "remote_addr": "localhost",
            # Load media and save screenshots and traces for debugging
            "load_media": True,
            "tracing": True,
            "screenshots": True,
            # Load credentials from .env file via dotenv lib
            "email": os.environ["EMAIL"],
            "password": os.environ["PASSWORD"],
        },
        cookies,
    )
    # Login if no cookies there or cookies are invalid
    await cookidoo.login(
        # force_session_refresh=True, # Use to force a login, even for valid cookies
        # captcha_recovery_mode="user_input" # Enable captcha recovery mode
    )
    # Save the newly created cookies locally
    save_cookies(cookidoo.cookies)

    # Clear all items in shopping list
    await cookidoo.clear_items()

    # Add items from recipe, check all of and remove them again
    await cookidoo.add_items("r59322")
    items = await cookidoo.get_items(checked=True, pending=True)
    for item in items:
        item["state"] = "pending" if item["state"] == "checked" else "checked"
    await cookidoo.update_items(items)
    await cookidoo.remove_items("r59322")

    # Add additional items, check them off and remove them again
    await cookidoo.create_additional_items(["Chocolate", "Apple", "Water"])
    additional_items = await cookidoo.get_additional_items(checked=True, pending=True)
    for additional_item in additional_items:
        additional_item["state"] = (
            "pending" if additional_item["state"] == "checked" else "checked"
        )
        if additional_item["label"] == "Chocolate":
            additional_item["label"] = "Toblerone"
    await cookidoo.update_additional_items(additional_items)
    await cookidoo.delete_additional_items(additional_items)

    # Save the cookies again, as on each call they are validated and maybe refreshed - it is good practise
    save_cookies(cookidoo.cookies)


asyncio.run(main())
