"""Test the native runner."""

import asyncio

from playwright.async_api import async_playwright


async def main():
    """Test on the native browser through debug port to reach the playwright page and save a screenshot."""
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        page = await browser.new_page()
        await page.goto("http://playwright.dev")
        await page.screenshot(path="out/kasmvnc/example.png")
        await browser.close()


asyncio.run(main())
