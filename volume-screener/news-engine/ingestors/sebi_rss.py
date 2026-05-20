"""
SEBI RSS Parser

Parses SEBI (Securities and Exchange Board of India) circulars and notices.
These are regulatory filings that can significantly impact market sentiment.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any
import feedparser

logger = logging.getLogger(__name__)


class SEBIRSSParser:
    """
    Parser for SEBI regulatory feeds.
    
    Monitors:
    - SEBI Circulars
    - Press Releases
    - Board Decisions
    """
    
    # SEBI RSS feeds
    FEEDS = {
        "circulars": "https://www.sebi.gov.in/sebi_rss.xml",
        # Note: SEBI's main RSS may not always be available
        # Fallback to scraping if needed
    }
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
    
    def fetch_circulars(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Fetch latest SEBI circulars from RSS.
        
        Returns:
            List of regulatory news items
        """
        all_items = []
        
        for feed_name, feed_url in self.FEEDS.items():
            try:
                logger.info(f"📡 Fetching SEBI {feed_name}...")
                
                feed = feedparser.parse(feed_url)
                
                if feed.bozo and feed.bozo_exception:
                    logger.warning(f"⚠️ SEBI feed parse warning: {feed.bozo_exception}")
                
                entries = feed.entries[:limit]
                
                for entry in entries:
                    try:
                        # Extract fields
                        headline = entry.get("title", "").strip()
                        link = entry.get("link", "")
                        
                        # Parse published date
                        published = entry.get("published_parsed") or entry.get("updated_parsed")
                        if published:
                            pub_dt = datetime(*published[:6])
                        else:
                            pub_dt = datetime.utcnow()
                        
                        # Extract description/summary
                        summary = entry.get("summary", entry.get("description", ""))
                        if summary:
                            summary = summary[:500]  # Truncate
                        
                        if len(headline) < 10:
                            continue
                        
                        all_items.append({
                            "headline": headline,
                            "link": link,
                            "source": "SEBI",
                            "source_name": "SEBI",
                            "timestamp": pub_dt.isoformat(),
                            "published_at": pub_dt.isoformat(),
                            "ticker": "MARKET",  # Regulatory affects whole market
                            "category": "regulatory",
                            "raw_body": summary,
                        })
                        
                    except Exception as e:
                        logger.debug(f"Error parsing SEBI entry: {e}")
                        continue
                
                logger.info(f"📰 SEBI {feed_name}: Got {len(entries)} items")
                
            except Exception as e:
                logger.error(f"❌ SEBI feed error ({feed_name}): {e}")
        
        return all_items[:limit]
    
    def categorize_circular(self, headline: str) -> Dict[str, Any]:
        """
        Categorize SEBI circular by type and impact.
        
        Returns dict with:
            - category: Type of circular
            - impact: Expected market impact (high/medium/low)
        """
        headline_lower = headline.lower()
        
        # High impact keywords
        if any(kw in headline_lower for kw in [
            "ban", "penalty", "fine", "suspend", "debarr",
            "investigation", "prosecution", "fraud"
        ]):
            return {"category": "enforcement", "impact": "high"}
        
        # Medium impact
        if any(kw in headline_lower for kw in [
            "amendment", "revision", "new regulation", "framework",
            "margin", "limit", "disclosure"
        ]):
            return {"category": "regulation_change", "impact": "medium"}
        
        # Low impact
        if any(kw in headline_lower for kw in [
            "clarification", "corrigendum", "extension", "holiday"
        ]):
            return {"category": "administrative", "impact": "low"}
        
        # Default
        return {"category": "general", "impact": "medium"}


# Quick test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    parser = SEBIRSSParser()
    
    print("=" * 60)
    print("🧪 Testing SEBI RSS Parser")
    print("=" * 60)
    
    circulars = parser.fetch_circulars(limit=10)
    
    print(f"\n📰 Got {len(circulars)} circulars:\n")
    
    for i, item in enumerate(circulars, 1):
        cat_info = parser.categorize_circular(item["headline"])
        impact_emoji = "🔴" if cat_info["impact"] == "high" else "🟡" if cat_info["impact"] == "medium" else "🟢"
        
        print(f"{i}. {impact_emoji} [{cat_info['category']}] {item['headline'][:60]}...")
        print(f"   Published: {item['timestamp']}")
        print()
