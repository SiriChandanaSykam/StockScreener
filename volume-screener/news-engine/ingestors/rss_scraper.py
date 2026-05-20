"""
RSS News Scraper - Multi-Source Financial News Ingestion

Fetches real-time news from trusted Indian financial sources:
- Moneycontrol
- Economic Times
- Business Standard
- LiveMint
- Reuters India

Each source is configured with:
- RSS feed URL
- Category classification
- Polling frequency recommendation
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import re

import httpx
import feedparser
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)

# ============================================================
# DATA STRUCTURES
# ============================================================

@dataclass
class RSSNewsItem:
    """Normalized news item from any RSS source"""
    title: str
    link: str
    published_at: datetime
    summary: str
    source_name: str
    category: str
    raw_data: Dict[str, Any]
    
    # Optional extracted fields
    author: Optional[str] = None
    image_url: Optional[str] = None
    tags: Optional[List[str]] = None


@dataclass
class RSSFeedConfig:
    """Configuration for an RSS feed source"""
    name: str
    url: str
    category: str = "market_news"
    poll_interval_seconds: int = 300  # 5 minutes default
    enabled: bool = True
    
    # Optional customization
    title_prefix_strip: Optional[str] = None  # Strip common prefixes
    max_items: int = 50


# ============================================================
# FEED CONFIGURATIONS
# ============================================================

FEED_CONFIGS: List[RSSFeedConfig] = [
    # ============================================================
    # INDIAN MARKET SOURCES (Primary - High Frequency)
    # ============================================================
    RSSFeedConfig(
        name="Moneycontrol",
        url="https://www.moneycontrol.com/rss/latestnews.xml",
        category="market_news",
        poll_interval_seconds=300,  # 5 min
    ),
    RSSFeedConfig(
        name="Moneycontrol Markets",
        url="https://www.moneycontrol.com/rss/marketreports.xml",
        category="market_report",
        poll_interval_seconds=300,
    ),
    RSSFeedConfig(
        name="Economic Times Markets",
        url="https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
        category="market_news",
        poll_interval_seconds=300,
    ),
    RSSFeedConfig(
        name="Economic Times Stocks",
        url="https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms",
        category="stock_news",
        poll_interval_seconds=300,
    ),
    RSSFeedConfig(
        name="ET Economy",
        url="https://economictimes.indiatimes.com/news/economy/rssfeeds/1373380680.cms",
        category="economy",
        poll_interval_seconds=300,
    ),
    
    # ============================================================
    # INDIAN BUSINESS NEWS (24/7)
    # ============================================================
    RSSFeedConfig(
        name="Business Standard Markets",
        url="https://www.business-standard.com/rss/markets-106.rss",
        category="market_analysis",
        poll_interval_seconds=600,  # 10 min
    ),
    RSSFeedConfig(
        name="Business Standard Economy",
        url="https://www.business-standard.com/rss/economy-102.rss",
        category="economy",
        poll_interval_seconds=600,
    ),
    RSSFeedConfig(
        name="LiveMint Markets",
        url="https://www.livemint.com/rss/markets",
        category="market_news",
        poll_interval_seconds=600,
    ),
    RSSFeedConfig(
        name="LiveMint Companies",
        url="https://www.livemint.com/rss/companies",
        category="company_news",
        poll_interval_seconds=600,
    ),
    
    # ============================================================
    # GLOBAL / INTERNATIONAL NEWS (24/7 - Covers overnight)
    # ============================================================
    RSSFeedConfig(
        name="Reuters India Business",
        url="https://feeds.reuters.com/reuters/INbusinessNews",
        category="macro_news",
        poll_interval_seconds=600,
    ),
    RSSFeedConfig(
        name="Reuters World Markets",
        url="https://feeds.reuters.com/reuters/businessNews",
        category="global_markets",
        poll_interval_seconds=600,
    ),
    RSSFeedConfig(
        name="Yahoo Finance",
        url="https://finance.yahoo.com/news/rssindex",
        category="global_markets",
        poll_interval_seconds=600,
    ),
    RSSFeedConfig(
        name="CNBC Top News",
        url="https://www.cnbc.com/id/100003114/device/rss/rss.html",
        category="global_markets",
        poll_interval_seconds=600,
    ),
    RSSFeedConfig(
        name="Investing.com News",
        url="https://www.investing.com/rss/news.rss",
        category="global_markets",
        poll_interval_seconds=600,
    ),
    
    # ============================================================
    # POLICY & REGULATORY (Important for market sentiment)
    # ============================================================
    RSSFeedConfig(
        name="RBI Press Releases",
        url="https://www.rbi.org.in/scripts/RSS.aspx",
        category="regulatory",
        poll_interval_seconds=900,  # 15 min
    ),
]


# ============================================================
# RSS PARSER
# ============================================================

class RSSNewsScraper:
    """
    Generic RSS feed scraper with:
    - Async HTTP fetching
    - Feed parsing with feedparser
    - Date normalization
    - Error handling and retries
    """
    
    def __init__(
        self,
        configs: Optional[List[RSSFeedConfig]] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        self.configs = configs or FEED_CONFIGS
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) NewsBot/1.0",
                    "Accept": "application/rss+xml, application/xml, text/xml",
                },
                follow_redirects=True,
            )
        return self._client
    
    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    def _parse_date(self, date_str: Optional[str]) -> datetime:
        """Parse various date formats to UTC datetime"""
        if not date_str:
            return datetime.now(timezone.utc)
        
        try:
            # feedparser sometimes returns struct_time
            if hasattr(date_str, 'tm_year'):
                import time
                return datetime.fromtimestamp(time.mktime(date_str), tz=timezone.utc)
            
            # Try dateutil parser
            dt = date_parser.parse(date_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return datetime.now(timezone.utc)
    
    def _clean_html(self, text: str) -> str:
        """Remove HTML tags from text"""
        if not text:
            return ""
        # Remove HTML tags
        clean = re.sub(r'<[^>]+>', '', text)
        # Normalize whitespace
        clean = re.sub(r'\s+', ' ', clean).strip()
        return clean
    
    def _extract_image(self, entry: Dict) -> Optional[str]:
        """Try to extract image URL from feed entry"""
        # Check media:content
        if 'media_content' in entry:
            for media in entry.get('media_content', []):
                if media.get('type', '').startswith('image'):
                    return media.get('url')
        
        # Check enclosures
        for enclosure in entry.get('enclosures', []):
            if enclosure.get('type', '').startswith('image'):
                return enclosure.get('href') or enclosure.get('url')
        
        # Check for image in summary
        summary = entry.get('summary', '')
        img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', summary)
        if img_match:
            return img_match.group(1)
        
        return None
    
    def _extract_tags(self, entry: Dict) -> List[str]:
        """Extract tags/categories from entry"""
        tags = []
        
        for tag in entry.get('tags', []):
            if isinstance(tag, dict):
                tags.append(tag.get('term', ''))
            else:
                tags.append(str(tag))
        
        return [t for t in tags if t]
    
    async def fetch_feed(self, config: RSSFeedConfig) -> List[RSSNewsItem]:
        """Fetch and parse a single RSS feed"""
        items = []
        
        try:
            client = await self._get_client()
            
            logger.info(f"📡 Fetching RSS: {config.name} from {config.url}")
            response = await client.get(config.url)
            response.raise_for_status()
            
            # Parse feed
            feed = feedparser.parse(response.text)
            
            if feed.bozo and feed.bozo_exception:
                logger.warning(f"Feed parse warning for {config.name}: {feed.bozo_exception}")
            
            for entry in feed.entries[:config.max_items]:
                try:
                    # Extract and normalize data
                    title = self._clean_html(entry.get('title', ''))
                    if config.title_prefix_strip and title.startswith(config.title_prefix_strip):
                        title = title[len(config.title_prefix_strip):].strip()
                    
                    link = entry.get('link', '')
                    summary = self._clean_html(
                        entry.get('summary', '') or entry.get('description', '')
                    )
                    
                    # Parse date
                    pub_date = entry.get('published_parsed') or entry.get('updated_parsed')
                    if pub_date is None:
                        pub_date = entry.get('published') or entry.get('updated')
                    published_at = self._parse_date(pub_date)
                    
                    item = RSSNewsItem(
                        title=title,
                        link=link,
                        published_at=published_at,
                        summary=summary[:500] if summary else "",  # Truncate long summaries
                        source_name=config.name,
                        category=config.category,
                        author=entry.get('author'),
                        image_url=self._extract_image(entry),
                        tags=self._extract_tags(entry),
                        raw_data=dict(entry),
                    )
                    items.append(item)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse entry from {config.name}: {e}")
                    continue
            
            logger.info(f"✅ Parsed {len(items)} items from {config.name}")
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching {config.name}: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"Request error fetching {config.name}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching {config.name}: {e}")
        
        return items
    
    async def fetch_all_feeds(
        self,
        source_names: Optional[List[str]] = None,
    ) -> List[RSSNewsItem]:
        """
        Fetch all configured feeds (or specific ones by name).
        Returns combined list of news items.
        """
        all_items = []
        
        # Filter configs if specific sources requested
        configs_to_fetch = self.configs
        if source_names:
            configs_to_fetch = [
                c for c in self.configs 
                if c.name in source_names and c.enabled
            ]
        else:
            configs_to_fetch = [c for c in self.configs if c.enabled]
        
        # Fetch all feeds concurrently
        tasks = [self.fetch_feed(config) for config in configs_to_fetch]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Feed fetch failed: {result}")
            elif isinstance(result, list):
                all_items.extend(result)
        
        # Sort by published date (newest first)
        all_items.sort(key=lambda x: x.published_at, reverse=True)
        
        logger.info(f"📰 Total items fetched: {len(all_items)} from {len(configs_to_fetch)} sources")
        
        return all_items


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

async def fetch_latest_news(
    sources: Optional[List[str]] = None,
    max_items: int = 100,
) -> List[RSSNewsItem]:
    """
    Quick function to fetch latest news from configured sources.
    
    Args:
        sources: Optional list of source names to fetch (None = all)
        max_items: Maximum items to return
    
    Returns:
        List of RSSNewsItem sorted by date (newest first)
    """
    scraper = RSSNewsScraper()
    try:
        items = await scraper.fetch_all_feeds(source_names=sources)
        return items[:max_items]
    finally:
        await scraper.close()


def get_enabled_sources() -> List[str]:
    """Get list of enabled source names"""
    return [c.name for c in FEED_CONFIGS if c.enabled]


def get_source_config(name: str) -> Optional[RSSFeedConfig]:
    """Get config for a specific source by name"""
    for config in FEED_CONFIGS:
        if config.name == name:
            return config
    return None


# ============================================================
# CLI TEST
# ============================================================

if __name__ == "__main__":
    import sys
    
    async def main():
        print("🧪 Testing RSS News Scraper\n")
        print(f"Configured sources: {get_enabled_sources()}\n")
        
        # Test specific sources
        sources_to_test = ["Moneycontrol", "Economic Times Markets"]
        
        print(f"Fetching from: {sources_to_test}\n")
        items = await fetch_latest_news(sources=sources_to_test, max_items=10)
        
        print(f"\n📰 Found {len(items)} items:\n")
        for i, item in enumerate(items[:10], 1):
            print(f"{i}. [{item.source_name}] {item.title[:60]}...")
            print(f"   📅 {item.published_at.strftime('%Y-%m-%d %H:%M')}")
            print(f"   🔗 {item.link[:50]}...")
            print()
    
    asyncio.run(main())
