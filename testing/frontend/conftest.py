"""
Playwright E2E Test Configuration
Run with: pytest testing/frontend/ -v
"""
import pytest
from playwright.async_api import async_playwright


@pytest.fixture(scope="session")
async def browser():
    """Create Playwright browser session"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest.fixture
async def page(browser):
    """Create new page for each test"""
    context = await browser.new_context()
    page = await context.new_page()
    yield page
    await context.close()
