"""
Moneycontrol News Scraper

Scrapes latest news headlines from Moneycontrol markets section.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class MoneycontrolScraper:
    """
    Scraper for Moneycontrol market news.
    
    Scrapes:
    - Market news headlines
    - Stock-specific news
    - Sector news
    """
    
    BASE_URL = "https://www.moneycontrol.com"
    MARKET_NEWS_URL = f"{BASE_URL}/news/business/markets/"
    
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
    }
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
    
    def scrape_headlines(self, limit: int = 30) -> List[Dict[str, Any]]:
        """
        Scrape latest headlines from Moneycontrol markets.
        
        Returns:
            List of news items with headline, link, source, timestamp
        """
        try:
            response = self.session.get(
                self.MARKET_NEWS_URL,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, "html.parser")
            news_items = []
            
            # Find news list items
            # Moneycontrol uses <li> with class "clearfix" for news items
            articles = soup.select("li.clearfix")[:limit]
            
            if not articles:
                # Fallback: try h2 with anchor tags
                articles = soup.find_all("h2")[:limit]
            
            for article in articles:
                try:
                    # Try to find anchor tag
                    link_elem = article.find("a")
                    if not link_elem:
                        continue
                    
                    headline = link_elem.get_text(strip=True)
                    link = link_elem.get("href", "")
                    
                    # Skip if headline is too short or is a category
                    if len(headline) < 20:
                        continue
                    
                    # Make link absolute
                    if link and not link.startswith("http"):
                        link = f"{self.BASE_URL}{link}"
                    
                    # Check for duplicates
                    if any(n["headline"] == headline for n in news_items):
                        continue
                    
                    news_items.append({
                        "headline": headline,
                        "link": link,
                        "source": "Moneycontrol",
                        "source_name": "Moneycontrol",
                        "timestamp": datetime.utcnow().isoformat(),
                        "ticker": "MARKET",  # Generic, can be extracted later
                        "category": "market_news",
                    })
                    
                except Exception as e:
                    logger.debug(f"Error parsing article: {e}")
                    continue
            
            logger.info(f"📰 Moneycontrol: Scraped {len(news_items)} headlines")
            return news_items
            
        except requests.RequestException as e:
            logger.error(f"❌ Moneycontrol scraping failed: {e}")
            return []
    
    def scrape_stock_news(self, ticker: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Scrape news for a specific stock ticker.
        
        Args:
            ticker: NSE ticker symbol (e.g., "RELIANCE")
            limit: Max headlines to return
            
        Returns:
            List of news items related to the ticker
        """
        try:
            # Moneycontrol stock news URL pattern
            search_url = f"{self.BASE_URL}/news/tags/{ticker.lower()}.html"
            
            response = self.session.get(search_url, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, "html.parser")
            news_items = []
            
            articles = soup.select("li.clearfix a")[:limit]
            
            for link_elem in articles:
                headline = link_elem.get_text(strip=True)
                link = link_elem.get("href", "")
                
                if len(headline) < 20:
                    continue
                
                if link and not link.startswith("http"):
                    link = f"{self.BASE_URL}{link}"
                
                news_items.append({
                    "headline": headline,
                    "link": link,
                    "source": "Moneycontrol",
                    "source_name": "Moneycontrol",
                    "timestamp": datetime.utcnow().isoformat(),
                    "ticker": ticker.upper(),
                    "category": "stock_news",
                })
            
            logger.info(f"📰 Moneycontrol: Scraped {len(news_items)} headlines for {ticker}")
            return news_items
            
        except requests.RequestException as e:
            logger.error(f"❌ Moneycontrol stock news failed for {ticker}: {e}")
            return []


# Quick test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    scraper = MoneycontrolScraper()
    
    print("=" * 60)
    print("🧪 Testing Moneycontrol Scraper")
    print("=" * 60)
    
    headlines = scraper.scrape_headlines(limit=10)
    
    print(f"\n📰 Got {len(headlines)} headlines:\n")
    
    for i, item in enumerate(headlines, 1):
        print(f"{i}. {item['headline'][:70]}...")
        print(f"   Link: {item['link'][:50]}...")
        print()
