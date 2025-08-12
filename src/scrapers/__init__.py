"""Scrapers package for SCAPO."""

from src.scrapers.base import BaseScraper
from src.scrapers.browser_base import BrowserBaseScraper
from src.scrapers.intelligent_browser_scraper import IntelligentBrowserScraper

__all__ = [
    "BaseScraper",
    "BrowserBaseScraper",
    "IntelligentBrowserScraper",
]