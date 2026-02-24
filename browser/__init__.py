#!/usr/bin/env python3
"""
PolyClaw Browser Automation

Playwright-based browser automation for interacting with Polymarket
and other prediction market platforms.

Inspired by OpenClaw's browser control system.
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field

logger = logging.getLogger("polyclaw.browser")

# Paths
POLYCLAW_DIR = Path.home() / ".polyclaw"
BROWSER_DIR = POLYCLAW_DIR / "browser"
SCREENSHOTS_DIR = BROWSER_DIR / "screenshots"
PROFILES_DIR = BROWSER_DIR / "profiles"

# Try to import playwright
try:
    from playwright.async_api import async_playwright, Browser, Page, BrowserContext
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    logger.warning("Playwright not installed. Run: pip install playwright && playwright install")


@dataclass
class BrowserConfig:
    """Browser configuration."""
    headless: bool = True
    slow_mo: int = 0  # Milliseconds between actions
    viewport_width: int = 1280
    viewport_height: int = 720
    user_agent: Optional[str] = None
    proxy: Optional[str] = None
    timeout: int = 30000  # Default timeout in ms
    downloads_path: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "headless": self.headless,
            "slow_mo": self.slow_mo,
            "viewport": {"width": self.viewport_width, "height": self.viewport_height},
            "user_agent": self.user_agent,
            "proxy": {"server": self.proxy} if self.proxy else None,
            "timeout": self.timeout
        }


@dataclass
class PageSnapshot:
    """Snapshot of a page state."""
    url: str
    title: str
    timestamp: datetime
    screenshot_path: Optional[str] = None
    html_content: Optional[str] = None
    elements: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "url": self.url,
            "title": self.title,
            "timestamp": self.timestamp.isoformat(),
            "screenshot_path": self.screenshot_path,
            "element_count": len(self.elements)
        }


class BrowserController:
    """
    Browser automation controller for prediction market interaction.
    
    Features:
    - Navigate to pages
    - Take snapshots
    - Extract data
    - Fill forms
    - Click elements
    - Monitor for changes
    """
    
    def __init__(self, config: BrowserConfig = None):
        if not HAS_PLAYWRIGHT:
            raise RuntimeError("Playwright not installed. Run: pip install playwright && playwright install")
        
        self.config = config or BrowserConfig()
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.snapshots: List[PageSnapshot] = []
        
        # Ensure directories exist
        BROWSER_DIR.mkdir(parents=True, exist_ok=True)
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    
    async def start(self):
        """Start the browser."""
        if self.browser:
            return
        
        self.playwright = await async_playwright().start()
        
        launch_options = {
            "headless": self.config.headless,
            "slow_mo": self.config.slow_mo
        }
        
        self.browser = await self.playwright.chromium.launch(**launch_options)
        
        context_options = {
            "viewport": {
                "width": self.config.viewport_width,
                "height": self.config.viewport_height
            }
        }
        
        if self.config.user_agent:
            context_options["user_agent"] = self.config.user_agent
        
        if self.config.proxy:
            context_options["proxy"] = {"server": self.config.proxy}
        
        self.context = await self.browser.new_context(**context_options)
        self.page = await self.context.new_page()
        
        # Set default timeout
        self.page.set_default_timeout(self.config.timeout)
        
        logger.info("Browser started")
    
    async def stop(self):
        """Stop the browser."""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        
        self.page = None
        self.context = None
        self.browser = None
        self.playwright = None
        
        logger.info("Browser stopped")
    
    async def navigate(self, url: str, wait_until: str = "networkidle") -> Dict:
        """Navigate to a URL."""
        if not self.page:
            await self.start()
        
        logger.info(f"Navigating to: {url}")
        response = await self.page.goto(url, wait_until=wait_until)
        
        return {
            "url": self.page.url,
            "status": response.status if response else None,
            "title": await self.page.title()
        }
    
    async def snapshot(self, save_screenshot: bool = True, save_html: bool = False) -> PageSnapshot:
        """Take a snapshot of the current page."""
        if not self.page:
            raise RuntimeError("Browser not started")
        
        timestamp = datetime.now()
        screenshot_path = None
        html_content = None
        
        if save_screenshot:
            filename = f"snapshot_{timestamp.strftime('%Y%m%d_%H%M%S')}.png"
            screenshot_path = str(SCREENSHOTS_DIR / filename)
            await self.page.screenshot(path=screenshot_path, full_page=True)
        
        if save_html:
            html_content = await self.page.content()
        
        # Extract visible elements
        elements = await self._extract_elements()
        
        snapshot = PageSnapshot(
            url=self.page.url,
            title=await self.page.title(),
            timestamp=timestamp,
            screenshot_path=screenshot_path,
            html_content=html_content,
            elements=elements
        )
        
        self.snapshots.append(snapshot)
        logger.info(f"Snapshot taken: {snapshot.url}")
        
        return snapshot
    
    async def _extract_elements(self) -> List[Dict]:
        """Extract interactive elements from the page."""
        elements = []
        
        # Extract buttons
        buttons = await self.page.query_selector_all("button, [role='button']")
        for i, btn in enumerate(buttons):
            text = await btn.inner_text()
            if text.strip():
                elements.append({
                    "type": "button",
                    "ref": f"btn_{i}",
                    "text": text.strip()[:50],
                    "visible": await btn.is_visible()
                })
        
        # Extract links
        links = await self.page.query_selector_all("a[href]")
        for i, link in enumerate(links):
            text = await link.inner_text()
            href = await link.get_attribute("href")
            if text.strip():
                elements.append({
                    "type": "link",
                    "ref": f"link_{i}",
                    "text": text.strip()[:50],
                    "href": href,
                    "visible": await link.is_visible()
                })
        
        # Extract inputs
        inputs = await self.page.query_selector_all("input, textarea, select")
        for i, inp in enumerate(inputs):
            inp_type = await inp.get_attribute("type") or "text"
            placeholder = await inp.get_attribute("placeholder") or ""
            elements.append({
                "type": "input",
                "ref": f"input_{i}",
                "input_type": inp_type,
                "placeholder": placeholder,
                "visible": await inp.is_visible()
            })
        
        return elements
    
    async def click(self, selector: str) -> bool:
        """Click an element."""
        if not self.page:
            raise RuntimeError("Browser not started")
        
        try:
            await self.page.click(selector)
            logger.info(f"Clicked: {selector}")
            return True
        except Exception as e:
            logger.error(f"Click failed: {e}")
            return False
    
    async def fill(self, selector: str, value: str) -> bool:
        """Fill an input field."""
        if not self.page:
            raise RuntimeError("Browser not started")
        
        try:
            await self.page.fill(selector, value)
            logger.info(f"Filled {selector}")
            return True
        except Exception as e:
            logger.error(f"Fill failed: {e}")
            return False
    
    async def type_text(self, selector: str, text: str, delay: int = 50) -> bool:
        """Type text into an element (simulates keystrokes)."""
        if not self.page:
            raise RuntimeError("Browser not started")
        
        try:
            await self.page.type(selector, text, delay=delay)
            return True
        except Exception as e:
            logger.error(f"Type failed: {e}")
            return False
    
    async def wait_for_selector(self, selector: str, timeout: int = None) -> bool:
        """Wait for an element to appear."""
        if not self.page:
            raise RuntimeError("Browser not started")
        
        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
            return True
        except Exception as e:
            logger.error(f"Wait failed: {e}")
            return False
    
    async def evaluate(self, script: str) -> Any:
        """Evaluate JavaScript in the page."""
        if not self.page:
            raise RuntimeError("Browser not started")
        
        return await self.page.evaluate(script)
    
    async def get_text(self, selector: str) -> Optional[str]:
        """Get text content of an element."""
        if not self.page:
            raise RuntimeError("Browser not started")
        
        try:
            element = await self.page.query_selector(selector)
            if element:
                return await element.inner_text()
        except Exception as e:
            logger.error(f"Get text failed: {e}")
        return None
    
    async def get_attribute(self, selector: str, attribute: str) -> Optional[str]:
        """Get attribute of an element."""
        if not self.page:
            raise RuntimeError("Browser not started")
        
        try:
            element = await self.page.query_selector(selector)
            if element:
                return await element.get_attribute(attribute)
        except Exception as e:
            logger.error(f"Get attribute failed: {e}")
        return None
    
    async def scroll(self, direction: str = "down", amount: int = 500):
        """Scroll the page."""
        if not self.page:
            raise RuntimeError("Browser not started")
        
        if direction == "down":
            await self.page.evaluate(f"window.scrollBy(0, {amount})")
        elif direction == "up":
            await self.page.evaluate(f"window.scrollBy(0, -{amount})")
        elif direction == "top":
            await self.page.evaluate("window.scrollTo(0, 0)")
        elif direction == "bottom":
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")


class PolymarketBrowser(BrowserController):
    """
    Specialized browser controller for Polymarket.
    """
    
    POLYMARKET_URL = "https://polymarket.com"
    
    async def open_polymarket(self):
        """Navigate to Polymarket."""
        return await self.navigate(self.POLYMARKET_URL)
    
    async def search_markets(self, query: str) -> List[Dict]:
        """Search for markets on Polymarket."""
        await self.navigate(f"{self.POLYMARKET_URL}/markets?q={query}")
        await self.wait_for_selector("[data-testid='market-card']", timeout=10000)
        
        # Extract market cards
        markets = await self.evaluate("""
            () => {
                const cards = document.querySelectorAll('[data-testid="market-card"]');
                return Array.from(cards).map(card => ({
                    title: card.querySelector('h3')?.innerText || '',
                    volume: card.querySelector('[data-testid="volume"]')?.innerText || '',
                    price: card.querySelector('[data-testid="price"]')?.innerText || ''
                }));
            }
        """)
        
        return markets
    
    async def get_market_details(self, market_slug: str) -> Dict:
        """Get details of a specific market."""
        await self.navigate(f"{self.POLYMARKET_URL}/event/{market_slug}")
        await asyncio.sleep(2)  # Wait for dynamic content
        
        # Extract market details
        details = await self.evaluate("""
            () => {
                return {
                    title: document.querySelector('h1')?.innerText || '',
                    description: document.querySelector('[data-testid="description"]')?.innerText || '',
                    volume: document.querySelector('[data-testid="total-volume"]')?.innerText || '',
                    outcomes: Array.from(document.querySelectorAll('[data-testid="outcome"]')).map(o => ({
                        name: o.querySelector('.outcome-name')?.innerText || '',
                        price: o.querySelector('.outcome-price')?.innerText || ''
                    }))
                };
            }
        """)
        
        return details
    
    async def get_wallet_profile(self, wallet_address: str) -> Dict:
        """Get wallet profile from Polymarket."""
        await self.navigate(f"{self.POLYMARKET_URL}/profile/{wallet_address}")
        await asyncio.sleep(2)
        
        profile = await self.evaluate("""
            () => {
                return {
                    username: document.querySelector('[data-testid="username"]')?.innerText || '',
                    pnl: document.querySelector('[data-testid="pnl"]')?.innerText || '',
                    positions: document.querySelector('[data-testid="positions-count"]')?.innerText || '',
                    volume: document.querySelector('[data-testid="volume"]')?.innerText || ''
                };
            }
        """)
        
        return profile
    
    async def monitor_market_prices(self, market_slug: str, interval: int = 5, callback: Callable = None):
        """Monitor market prices in real-time."""
        await self.navigate(f"{self.POLYMARKET_URL}/event/{market_slug}")
        
        while True:
            prices = await self.evaluate("""
                () => {
                    return Array.from(document.querySelectorAll('[data-testid="outcome"]')).map(o => ({
                        name: o.querySelector('.outcome-name')?.innerText || '',
                        price: o.querySelector('.outcome-price')?.innerText || ''
                    }));
                }
            """)
            
            if callback:
                callback(prices)
            else:
                logger.info(f"Prices: {prices}")
            
            await asyncio.sleep(interval)


# Convenience functions
async def take_polymarket_snapshot(url: str = None) -> PageSnapshot:
    """Take a snapshot of Polymarket."""
    browser = PolymarketBrowser()
    try:
        await browser.start()
        if url:
            await browser.navigate(url)
        else:
            await browser.open_polymarket()
        return await browser.snapshot()
    finally:
        await browser.stop()


async def scrape_market_data(market_slug: str) -> Dict:
    """Scrape data from a specific market."""
    browser = PolymarketBrowser()
    try:
        await browser.start()
        return await browser.get_market_details(market_slug)
    finally:
        await browser.stop()


# Sync wrappers for CLI use
def run_async(coro):
    """Run async function synchronously."""
    return asyncio.get_event_loop().run_until_complete(coro)


def snapshot_sync(url: str = None) -> PageSnapshot:
    """Synchronous wrapper for take_polymarket_snapshot."""
    return run_async(take_polymarket_snapshot(url))


def scrape_sync(market_slug: str) -> Dict:
    """Synchronous wrapper for scrape_market_data."""
    return run_async(scrape_market_data(market_slug))
