"""
BSE Corporate Announcements Scraper

Production-ready scraper for fetching corporate announcements from BSE India.
Fetches filings from the official BSE API with proper rate limiting,
retry logic, and user-agent rotation.

Usage:
    scraper = BSEScraper()
    announcements = await scraper.fetch(days_back=1)
"""

import asyncio
import random
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import httpx

# Handle both module and standalone imports
try:
    from .base import BaseIngestor
    from ..models import AnnouncementCreate
    from ..models.enums import SourceType, AnnouncementCategory
    from ..config import config
except ImportError:
    from base import BaseIngestor
    from models import AnnouncementCreate
    from models.enums import SourceType, AnnouncementCategory
    from config import config


class BSEScraper(BaseIngestor):
    """
    BSE India Corporate Announcements Scraper.
    
    Fetches corporate announcements from BSE's official API.
    Includes:
    - Rotating user agents to avoid blocking
    - Exponential backoff retry logic
    - Rate limiting
    - Clean data parsing
    """
    
    # BSE API endpoints
    BASE_URL = "https://api.bse.co.in/BseIndiaAPI/api"
    ANNOUNCEMENTS_ENDPOINT = "/AnnGetData/w"
    
    # PDF base URL for attachments
    PDF_BASE_URL = "https://www.bseindia.com/xml-data/corpfiling/AttachHis"
    
    def __init__(self):
        self._config = config.scraper
        self._client: Optional[httpx.AsyncClient] = None
        self._request_count = 0
        self._last_request_time: Optional[datetime] = None
    
    @property
    def source_name(self) -> str:
        return "BSE India"
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with random user agent."""
        return {
            "User-Agent": random.choice(self._config.user_agents),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Origin": "https://www.bseindia.com",
            "Referer": "https://www.bseindia.com/",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
        }
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with connection pooling."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._config.request_timeout),
                follow_redirects=True,
                limits=httpx.Limits(max_keepalive_connections=5),
            )
        return self._client
    
    async def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        if self._last_request_time:
            elapsed = (datetime.now() - self._last_request_time).total_seconds()
            min_interval = 60.0 / self._config.rate_limit_per_minute
            if elapsed < min_interval:
                await asyncio.sleep(min_interval - elapsed)
        self._last_request_time = datetime.now()
        self._request_count += 1
    
    async def _fetch_with_retry(
        self, 
        url: str, 
        params: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch URL with exponential backoff retry.
        
        Args:
            url: API endpoint URL
            params: Query parameters
            
        Returns:
            JSON response or None if all retries fail
        """
        client = await self._get_client()
        
        for attempt in range(self._config.max_retries):
            try:
                await self._rate_limit()
                
                response = await client.get(
                    url,
                    params=params,
                    headers=self._get_headers(),
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:  # Rate limited
                    wait_time = self._config.retry_delay * (2 ** attempt)
                    print(f"⚠️ BSE rate limited. Waiting {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    print(f"⚠️ BSE API returned {response.status_code}")
                    
            except httpx.TimeoutException:
                print(f"⚠️ BSE request timeout (attempt {attempt + 1})")
                await asyncio.sleep(self._config.retry_delay * (attempt + 1))
            except httpx.RequestError as e:
                print(f"⚠️ BSE request error: {e}")
                await asyncio.sleep(self._config.retry_delay)
        
        return None
    
    def _parse_bse_date(self, date_str: str) -> datetime:
        """
        Parse BSE date format to datetime.
        
        BSE uses format: "13 Jan 2026 15:30:45" or similar variants
        """
        formats = [
            "%d %b %Y %H:%M:%S",
            "%d-%b-%Y %H:%M:%S", 
            "%d/%m/%Y %H:%M:%S",
            "%d %b %Y",
            "%d-%b-%Y",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        
        # Fallback to current time if parsing fails
        print(f"⚠️ Could not parse BSE date: {date_str}")
        return datetime.now()
    
    def _build_pdf_url(self, attachment_name: Optional[str]) -> Optional[str]:
        """Build full PDF URL from attachment filename."""
        if not attachment_name:
            return None
        return f"{self.PDF_BASE_URL}/{attachment_name}"
    
    def _categorize_headline(self, headline: str) -> AnnouncementCategory:
        """
        Categorize announcement based on headline keywords.
        
        This is a basic rule-based categorization.
        Phase 3 will use AI for better classification.
        """
        headline_lower = headline.lower()
        
        # Financial Results
        if any(kw in headline_lower for kw in [
            "financial result", "quarterly result", "annual result",
            "unaudited", "audited", "standalone", "consolidated"
        ]):
            return AnnouncementCategory.FINANCIAL_RESULTS
        
        # Board Meeting
        if any(kw in headline_lower for kw in [
            "board meeting", "meeting of board", "board of directors"
        ]):
            return AnnouncementCategory.BOARD_MEETING
        
        # Dividend
        if "dividend" in headline_lower:
            return AnnouncementCategory.DIVIDEND
        
        # Bonus
        if "bonus" in headline_lower:
            return AnnouncementCategory.BONUS
        
        # Stock Split
        if "split" in headline_lower or "sub-division" in headline_lower:
            return AnnouncementCategory.STOCK_SPLIT
        
        # Acquisition/Merger
        if any(kw in headline_lower for kw in [
            "acquisition", "merger", "amalgamation", "takeover"
        ]):
            return AnnouncementCategory.ACQUISITION
        
        # Insider Trading
        if any(kw in headline_lower for kw in [
            "insider", "promoter", "shareholding pattern", "pit"
        ]):
            return AnnouncementCategory.INSIDER_TRADING
        
        # AGM/EGM
        if any(kw in headline_lower for kw in ["agm", "egm", "general meeting"]):
            return AnnouncementCategory.AGM_EGM
        
        # Rights Issue
        if "rights issue" in headline_lower:
            return AnnouncementCategory.RIGHTS_ISSUE
        
        # Buyback
        if "buyback" in headline_lower or "buy back" in headline_lower:
            return AnnouncementCategory.BUYBACK
        
        # Delisting
        if "delist" in headline_lower:
            return AnnouncementCategory.DELISTING
        
        # Regulatory
        if any(kw in headline_lower for kw in ["sebi", "regulation", "compliance"]):
            return AnnouncementCategory.REGULATORY
        
        return AnnouncementCategory.GENERAL
    
    def _parse_announcement(self, raw: Dict[str, Any]) -> Optional[AnnouncementCreate]:
        """
        Parse raw BSE API response into AnnouncementCreate.
        
        Args:
            raw: Single announcement from BSE API
            
        Returns:
            AnnouncementCreate object or None if parsing fails
        """
        try:
            # Extract required fields
            scrip_code = str(raw.get("SCRIP_CD", ""))
            company_name = raw.get("SLONGNAME", "") or raw.get("SCOMPNAME", "")
            headline = raw.get("HEADLINE", "") or raw.get("NEWSSUB", "")
            news_dt = raw.get("NEWS_DT", "") or raw.get("DT_TM", "")
            attachment = raw.get("ATTACHMENTNAME", "")
            
            # Skip if essential data missing
            if not scrip_code or not headline:
                return None
            
            # Parse timestamp
            timestamp = self._parse_bse_date(news_dt)
            
            # Build PDF link
            pdf_link = self._build_pdf_url(attachment)
            
            # Categorize
            category = self._categorize_headline(headline)
            
            return AnnouncementCreate(
                source=SourceType.BSE,
                ticker=scrip_code,
                company_name=company_name.strip(),
                headline=headline.strip(),
                timestamp=timestamp,
                pdf_link=pdf_link,
                category=category,
                raw_data=raw,
            )
            
        except Exception as e:
            print(f"⚠️ Error parsing BSE announcement: {e}")
            return None
    
    async def fetch(
        self,
        days_back: int = 1,
        category: str = "-1",  # -1 = all categories
        scrip_code: Optional[str] = None,
    ) -> List[AnnouncementCreate]:
        """
        Fetch corporate announcements from BSE.
        
        Args:
            days_back: Number of days to fetch (default 1 = today)
            category: BSE category filter (-1 for all)
            scrip_code: Optional specific scrip code to filter
            
        Returns:
            List of parsed AnnouncementCreate objects
        """
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # Format dates for BSE API (DD/MM/YYYY)
        from_date = start_date.strftime("%d/%m/%Y")
        to_date = end_date.strftime("%d/%m/%Y")
        
        # Build API URL
        url = f"{self.BASE_URL}{self.ANNOUNCEMENTS_ENDPOINT}"
        
        params = {
            "strCat": category,
            "strPrevDate": from_date,
            "strToDate": to_date,
            "strScrip": scrip_code or "",
            "strSearch": "",
            "strType": "C",  # Corporate announcements
        }
        
        print(f"📥 Fetching BSE announcements from {from_date} to {to_date}...")
        
        # Fetch data
        response = await self._fetch_with_retry(url, params)
        
        if not response:
            print("❌ Failed to fetch BSE announcements")
            return []
        
        # Handle both array and object responses
        if isinstance(response, dict):
            data = response.get("Table", response.get("data", []))
        elif isinstance(response, list):
            data = response
        else:
            data = []
        
        # Parse announcements
        announcements: List[AnnouncementCreate] = []
        for raw in data:
            parsed = self._parse_announcement(raw)
            if parsed:
                announcements.append(parsed)
        
        print(f"✅ Fetched {len(announcements)} BSE announcements")
        return announcements
    
    async def health_check(self) -> bool:
        """Check if BSE API is accessible."""
        try:
            client = await self._get_client()
            response = await client.get(
                "https://www.bseindia.com",
                headers=self._get_headers(),
                timeout=10,
            )
            return response.status_code == 200
        except Exception:
            return False
    
    async def close(self) -> None:
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Convenience function for standalone usage
async def fetch_bse_announcements(
    days_back: int = 1,
    category: str = "-1",
) -> List[Dict[str, Any]]:
    """
    Convenience function to fetch BSE announcements.
    
    Returns list of dictionaries with:
    - Time: Announcement timestamp
    - Ticker: BSE scrip code
    - Title: Headline
    - PDF_Link: Link to PDF attachment
    - Category: Detected category
    - Company: Company name
    
    Example:
        announcements = await fetch_bse_announcements(days_back=1)
        for ann in announcements:
            print(f"{ann['Ticker']}: {ann['Title']}")
    """
    scraper = BSEScraper()
    try:
        raw_announcements = await scraper.fetch(days_back=days_back, category=category)
        
        return [
            {
                "Time": ann.timestamp.isoformat(),
                "Ticker": ann.ticker,
                "Title": ann.headline,
                "PDF_Link": ann.pdf_link,
                "Category": ann.category.value,
                "Company": ann.company_name,
            }
            for ann in raw_announcements
        ]
    finally:
        await scraper.close()


# CLI test
if __name__ == "__main__":
    import json
    
    async def test():
        print("=" * 60)
        print("BSE Corporate Announcements Scraper Test")
        print("=" * 60)
        
        announcements = await fetch_bse_announcements(days_back=1)
        
        print(f"\nTotal announcements: {len(announcements)}\n")
        
        # Show first 5
        for ann in announcements[:5]:
            print(f"📢 [{ann['Category'].upper()}] {ann['Ticker']}")
            print(f"   {ann['Title'][:80]}...")
            print(f"   🕐 {ann['Time']}")
            if ann['PDF_Link']:
                print(f"   📎 {ann['PDF_Link']}")
            print()
        
        # Save to file
        with open("bse_announcements_sample.json", "w") as f:
            json.dump(announcements[:20], f, indent=2)
        print(f"💾 Saved sample to bse_announcements_sample.json")
    
    asyncio.run(test())
