"""Test the executable runner."""

import asyncio

from playwright.async_api import async_playwright


async def main():
    """Test each browser to reach the playwright page and save a screenshot."""
    async with async_playwright() as p:
        for browser_type in [p.chromium, p.firefox, p.webkit]:
            browser = await browser_type.launch(headless=True)
            page = await browser.new_page()
            await page.goto("http://playwright.dev")
            await page.screenshot(
                path=f"out/executable/example-{browser_type.name}.png"
            )
            await browser.close()


asyncio.run(main())
