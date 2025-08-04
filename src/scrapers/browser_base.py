"""Browser-based scraper base class using Playwright."""

from abc import abstractmethod
from typing import Any, Dict, List, Optional
import asyncio

from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from tenacity import retry, stop_after_attempt, wait_exponential

from src.core.logging import LogContext, get_logger
from src.core.models import ScrapedPost, SourceType
from src.scrapers.base import BaseScraper


class BrowserBaseScraper(BaseScraper):
    """Base class for scrapers that need JavaScript rendering."""
    
    def __init__(self, source_type: SourceType, headless: bool = True) -> None:
        super().__init__(source_type)
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.playwright = None
        
        # Browser configuration
        self.browser_args = [
            '--disable-blink-features=AutomationControlled',
            '--disable-features=IsolateOrigins,site-per-process',
        ]
        
    async def initialize_browser(self) -> None:
        """Initialize Playwright browser."""
        if not self.playwright:
            self.playwright = await async_playwright().start()
            
        if not self.browser:
            self.logger.info("Starting browser", headless=self.headless)
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=self.browser_args,
            )
            
        if not self.context:
            # Create context with anti-detection measures
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                java_script_enabled=True,
                ignore_https_errors=True,
            )
            
            # Add stealth scripts
            await self.context.add_init_script("""
                // Override navigator properties
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // Mock permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: 'denied' }) :
                        originalQuery(parameters)
                );
            """)
    
    async def close_browser(self) -> None:
        """Close browser and cleanup."""
        if self.context:
            await self.context.close()
            self.context = None
            
        if self.browser:
            await self.browser.close()
            self.browser = None
            
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
    
    async def authenticate(self) -> None:
        """Initialize browser for authentication."""
        await self.initialize_browser()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True,
    )
    async def navigate_and_wait(
        self, 
        page: Page, 
        url: str, 
        wait_selector: Optional[str] = None,
        timeout: int = 30000
    ) -> None:
        """Navigate to URL and wait for content to load."""
        try:
            await page.goto(url, wait_until='networkidle', timeout=timeout)
            
            if wait_selector:
                await page.wait_for_selector(wait_selector, timeout=timeout)
                
        except Exception as e:
            self.logger.error(f"Navigation failed to {url}: {e}")
            raise
    
    async def scroll_and_load(
        self, 
        page: Page, 
        max_scrolls: int = 5,
        scroll_delay: float = 1.0
    ) -> None:
        """Scroll page to load dynamic content."""
        for i in range(max_scrolls):
            # Scroll to bottom
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            
            # Wait for new content
            await asyncio.sleep(scroll_delay)
            
            # Check if we've reached the end
            at_bottom = await page.evaluate('''
                window.innerHeight + window.scrollY >= document.body.offsetHeight
            ''')
            
            if at_bottom:
                self.logger.debug(f"Reached bottom after {i+1} scrolls")
                break
    
    async def extract_with_js(
        self, 
        page: Page, 
        js_expression: str
    ) -> Any:
        """Extract data using JavaScript evaluation."""
        try:
            return await page.evaluate(js_expression)
        except Exception as e:
            self.logger.error(f"JS extraction failed: {e}")
            return None
    
    async def wait_for_ajax(
        self, 
        page: Page, 
        timeout: int = 5000
    ) -> None:
        """Wait for AJAX requests to complete."""
        try:
            # Wait for no network activity
            await page.wait_for_load_state('networkidle', timeout=timeout)
        except:
            # Timeout is okay, we tried our best
            pass
    
    async def handle_pagination(
        self,
        page: Page,
        next_button_selector: str,
        content_extractor,
        max_pages: int = 10
    ) -> List[Any]:
        """Handle pagination and extract content from multiple pages."""
        all_content = []
        
        for page_num in range(max_pages):
            self.logger.debug(f"Processing page {page_num + 1}")
            
            # Extract content from current page
            content = await content_extractor(page)
            all_content.extend(content)
            
            # Try to go to next page
            try:
                next_button = await page.query_selector(next_button_selector)
                if not next_button:
                    self.logger.debug("No more pages")
                    break
                
                # Click and wait for navigation
                await next_button.click()
                await self.wait_for_ajax(page)
                
            except Exception as e:
                self.logger.debug(f"Pagination ended: {e}")
                break
        
        return all_content
    
    async def intercept_api_calls(
        self,
        page: Page,
        api_pattern: str
    ) -> List[Dict[str, Any]]:
        """Intercept API calls to get data directly."""
        intercepted_data = []
        
        async def handle_response(response):
            if api_pattern in response.url:
                try:
                    data = await response.json()
                    intercepted_data.append({
                        'url': response.url,
                        'status': response.status,
                        'data': data
                    })
                except:
                    pass
        
        page.on('response', handle_response)
        return intercepted_data
    
    async def scrape_with_browser(
        self,
        url: str,
        content_extractor,
        **kwargs
    ) -> Dict[str, Any]:
        """Generic browser-based scraping method."""
        page = None
        try:
            # Create new page
            page = await self.context.new_page()
            
            # Navigate to URL
            await self.navigate_and_wait(page, url, **kwargs)
            
            # Extract content
            content = await content_extractor(page)
            
            return {
                'status': 'success',
                'content': content,
                'url': url
            }
            
        except Exception as e:
            self.logger.error(f"Browser scraping failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'url': url
            }
            
        finally:
            if page:
                await page.close()
    
    async def close(self):
        """Clean up browser resources."""
        await self.close_browser()
    
    # Make sure to close browser on cleanup
    async def __aenter__(self):
        await self.initialize_browser()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close_browser()


class PlaywrightForumScraper(BrowserBaseScraper):
    """Example implementation for forums that need JS rendering."""
    
    def __init__(self):
        super().__init__(SourceType.FORUM)
    
    async def fetch_posts(
        self,
        subreddit: Optional[str] = None,
        limit: int = 100,
        time_filter: str = "week",
    ) -> List[ScrapedPost]:
        """Fetch posts using browser automation."""
        posts = []
        
        # Example: Scrape a React-based forum
        async def extract_posts(page: Page) -> List[Dict[str, Any]]:
            # Wait for posts to load
            await page.wait_for_selector('.post-container', timeout=10000)
            
            # Extract posts using JS
            posts_data = await page.evaluate('''
                Array.from(document.querySelectorAll('.post-container')).map(post => ({
                    title: post.querySelector('.post-title')?.textContent || '',
                    content: post.querySelector('.post-content')?.textContent || '',
                    author: post.querySelector('.post-author')?.textContent || '',
                    score: parseInt(post.querySelector('.post-score')?.textContent || '0'),
                    url: post.querySelector('.post-link')?.href || '',
                    timestamp: post.querySelector('.post-time')?.getAttribute('datetime') || ''
                }))
            ''')
            
            return posts_data
        
        # Scrape the forum
        result = await self.scrape_with_browser(
            url='https://forum.example.com/latest',
            content_extractor=extract_posts,
            wait_selector='.post-container'
        )
        
        if result['status'] == 'success':
            # Convert to ScrapedPost objects
            for post_data in result['content']:
                # Process and create ScrapedPost
                # ... implementation ...
                pass
        
        return posts
    
    def extract_best_practices(self, posts: List[ScrapedPost]) -> Dict[str, Any]:
        """Extract best practices from posts."""
        # Implementation similar to existing forum scraper
        return {}