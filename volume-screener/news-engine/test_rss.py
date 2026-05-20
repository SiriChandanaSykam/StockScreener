"""
Test RSS Scraper - Verify feeds are working
"""

import asyncio
import sys
import os

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ingestors'))

# Import RSS scraper directly (avoid bse_scraper which has complex deps)
from rss_scraper import (
    fetch_latest_news,
    get_enabled_sources,
    RSSNewsScraper,
    FEED_CONFIGS,
)


async def test_individual_feeds():
    """Test each feed individually"""
    print("=" * 60)
    print("TEST: Individual Feed Parsing")
    print("=" * 60)
    
    scraper = RSSNewsScraper()
    
    for config in FEED_CONFIGS[:4]:  # Test first 4 sources
        print(f"\n📡 Testing: {config.name}")
        print(f"   URL: {config.url}")
        
        try:
            items = await scraper.fetch_feed(config)
            if items:
                print(f"   ✅ SUCCESS: {len(items)} items")
                print(f"   📰 Latest: {items[0].title[:50]}...")
                print(f"   📅 Date: {items[0].published_at}")
            else:
                print(f"   ⚠️ No items returned")
        except Exception as e:
            print(f"   ❌ FAILED: {e}")
    
    await scraper.close()


async def test_combined_fetch():
    """Test fetching from all sources"""
    print("\n" + "=" * 60)
    print("TEST: Combined Fetch (Priority Sources)")
    print("=" * 60)
    
    priority_sources = ["Moneycontrol", "Economic Times Markets"]
    items = await fetch_latest_news(sources=priority_sources, max_items=20)
    
    print(f"\n📰 Total items: {len(items)}")
    print("\nLatest 10 headlines:\n")
    
    for i, item in enumerate(items[:10], 1):
        print(f"{i:2}. [{item.source_name}]")
        print(f"    {item.title[:60]}{'...' if len(item.title) > 60 else ''}")
        print(f"    🔗 {item.link[:50]}...")
        print()


async def main():
    print("\n🧪 RSS SCRAPER TEST SUITE\n")
    print(f"Configured sources: {get_enabled_sources()}\n")
    
    await test_individual_feeds()
    await test_combined_fetch()
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
