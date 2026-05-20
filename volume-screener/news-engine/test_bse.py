"""Test BSE Scraper - Run this to verify the scraper works."""
import asyncio
import sys
from pathlib import Path

# Ensure news-engine is in path
news_engine_path = Path(__file__).parent
sys.path.insert(0, str(news_engine_path))

# Now import using direct imports
import httpx
import random
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


# Inline minimal config for standalone test
@dataclass
class ScraperConfig:
    request_timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    rate_limit_per_minute: int = 30
    user_agents: List[str] = field(default_factory=lambda: [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    ])


async def fetch_bse_announcements(days_back: int = 1) -> List[Dict[str, Any]]:
    """Fetch BSE announcements directly (standalone test)."""
    
    config = ScraperConfig()
    
    # BSE API
    url = "https://api.bse.co.in/BseIndiaAPI/api/AnnGetData/w"
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    params = {
        "strCat": "-1",
        "strPrevDate": start_date.strftime("%d/%m/%Y"),
        "strToDate": end_date.strftime("%d/%m/%Y"),
        "strScrip": "",
        "strSearch": "",
        "strType": "C",
    }
    
    headers = {
        "User-Agent": random.choice(config.user_agents),
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://www.bseindia.com",
        "Referer": "https://www.bseindia.com/",
    }
    
    print(f"📥 Fetching BSE announcements from {params['strPrevDate']} to {params['strToDate']}...")
    
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url, params=params, headers=headers)
        
        if response.status_code != 200:
            print(f"❌ BSE API returned {response.status_code}")
            return []
        
        data = response.json()
        
        # Handle response format
        if isinstance(data, dict):
            items = data.get("Table", [])
        elif isinstance(data, list):
            items = data
        else:
            items = []
        
        announcements = []
        for raw in items:
            try:
                announcements.append({
                    "Time": raw.get("NEWS_DT", ""),
                    "Ticker": str(raw.get("SCRIP_CD", "")),
                    "Company": raw.get("SLONGNAME", "") or raw.get("SCOMPNAME", ""),
                    "Title": raw.get("HEADLINE", "") or raw.get("NEWSSUB", ""),
                    "PDF_Link": f"https://www.bseindia.com/xml-data/corpfiling/AttachHis/{raw.get('ATTACHMENTNAME', '')}" if raw.get("ATTACHMENTNAME") else None,
                })
            except:
                pass
        
        print(f"✅ Fetched {len(announcements)} announcements")
        return announcements


async def test():
    print("=" * 60)
    print("BSE Corporate Announcements Scraper Test")
    print("=" * 60)
    
    announcements = await fetch_bse_announcements(days_back=1)
    
    print(f"\nTotal announcements: {len(announcements)}\n")
    
    # Show first 10
    for i, ann in enumerate(announcements[:10], 1):
        print(f"{i}. 📢 {ann['Ticker']} - {ann['Company'][:40]}")
        print(f"   {ann['Title'][:70]}...")
        print(f"   🕐 {ann['Time']}")
        if ann['PDF_Link']:
            print(f"   📎 PDF available")
        print()
    
    return announcements


if __name__ == "__main__":
    result = asyncio.run(test())
    print(f"\n✅ Test complete! Fetched {len(result)} announcements.")
