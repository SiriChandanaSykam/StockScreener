"""
Diagnostic: Check RSS feed freshness
"""
import feedparser
from datetime import datetime

feeds = {
    "ET Markets": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "ET Stocks": "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms",
}

print("=" * 60)
print("📡 RSS Feed Freshness Check")
print(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

for name, url in feeds.items():
    print(f"\n📰 {name}")
    print("-" * 40)
    
    feed = feedparser.parse(url)
    
    if feed.bozo:
        print(f"   ⚠️ Parse error: {feed.bozo_exception}")
    
    print(f"   Total entries: {len(feed.entries)}")
    
    for i, entry in enumerate(feed.entries[:3], 1):
        title = entry.get("title", "No title")[:50]
        pub = entry.get("published", "No date")
        print(f"   {i}. [{pub}]")
        print(f"      {title}...")
