"""
Standalone RSS Fetch - No Celery dependency
Directly fetches and inserts RSS news into the database.
"""

import asyncio
import sys
import os
import uuid

# Add paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ingestors'))


async def fetch_and_store():
    from rss_scraper import fetch_latest_news
    from storage.database import async_session_maker, init_db
    from storage.models import NewsItem
    from sqlalchemy import select
    
    print("🔧 Initializing database...")
    await init_db()
    
    # Fetch from ET only (Moneycontrol gives 403)
    sources = ["Economic Times Markets", "Economic Times Stocks"]
    print(f"\n📡 Fetching from: {sources}")
    
    rss_items = await fetch_latest_news(sources=sources, max_items=50)
    print(f"📰 Received {len(rss_items)} items from RSS feeds")
    
    if not rss_items:
        print("⚠️ No items received!")
        return
    
    # Dedupe within batch
    seen_urls = set()
    unique_items = []
    for item in rss_items:
        if item.link and item.link not in seen_urls:
            seen_urls.add(item.link)
            unique_items.append(item)
    
    batch_dups = len(rss_items) - len(unique_items)
    print(f"📋 After batch dedupe: {len(unique_items)} unique items (removed {batch_dups})")
    
    new_count = 0
    dup_count = 0
    error_count = 0
    
    for rss_item in unique_items:
        async with async_session_maker() as session:
            try:
                # Check DB for existing URL
                existing = await session.execute(
                    select(NewsItem).where(NewsItem.source_url == rss_item.link)
                )
                if existing.scalar_one_or_none():
                    dup_count += 1
                    continue
                
                # Check DB for existing headline
                existing_headline = await session.execute(
                    select(NewsItem).where(NewsItem.headline == rss_item.title)
                )
                if existing_headline.scalar_one_or_none():
                    dup_count += 1
                    continue
                
                # Insert new item
                news_item = NewsItem(
                    id=uuid.uuid4(),
                    ticker="MARKET",
                    company_name=None,
                    headline=rss_item.title,
                    source_url=rss_item.link,
                    source_name=rss_item.source_name,
                    published_at=rss_item.published_at,
                    category=rss_item.category,
                    raw_body=rss_item.summary,
                    is_processed=False,
                    is_alerted=False,
                )
                session.add(news_item)
                await session.commit()
                new_count += 1
                print(f"  ✅ Added: {rss_item.title[:50]}...")
            except Exception as e:
                error_count += 1
                print(f"  ⚠️ Skipped (error): {str(e)[:50]}...")
    
    print(f"\n📊 RESULTS:")
    print(f"   New inserted: {new_count}")
    print(f"   Duplicates skipped: {dup_count}")
    print(f"   Errors: {error_count}")
    print(f"\n🎉 Done! Refresh your frontend to see the news.")


if __name__ == "__main__":
    asyncio.run(fetch_and_store())
