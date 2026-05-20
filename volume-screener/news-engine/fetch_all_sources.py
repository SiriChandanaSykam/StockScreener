"""
Multi-Source News Fetcher

Aggregates news from multiple sources:
- Economic Times (RSS)
- Moneycontrol (Web Scraping)
- SEBI (RSS)

Stores in database and optionally runs FinBERT analysis.
"""

import asyncio
import sys
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any

# Add paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ingestors'))


async def fetch_all_sources(
    include_et: bool = True,
    include_mc: bool = True,
    include_sebi: bool = True,
    max_per_source: int = 20
) -> List[Dict[str, Any]]:
    """
    Fetch news from all configured sources.
    """
    all_items = []
    
    # 1. All RSS Feeds (ET, Moneycontrol, Bloomberg, Reuters, etc.)
    if include_et:
        try:
            from rss_scraper import fetch_latest_news, get_enabled_sources
            enabled_sources = get_enabled_sources()
            print(f"📡 Fetching from {len(enabled_sources)} RSS sources...")
            
            # Fetch from ALL enabled sources
            et_items = await fetch_latest_news(sources=None, max_items=max_per_source * 3)
            print(f"   ✅ RSS: {len(et_items)} items from {len(enabled_sources)} feeds")
            
            for item in et_items:
                all_items.append({
                    "headline": item.title,
                    "link": item.link,
                    "source_name": item.source_name,
                    "published_at": item.published_at,
                    "category": item.category or "market_news",
                    "raw_body": item.summary,
                    "ticker": "MARKET",
                })
        except Exception as e:
            print(f"   ❌ RSS fetch failed: {e}")
    
    # 2. Moneycontrol (Web Scraping)
    if include_mc:
        try:
            from moneycontrol_scraper import MoneycontrolScraper
            print(f"📡 Fetching Moneycontrol...")
            mc = MoneycontrolScraper()
            mc_items = mc.scrape_headlines(limit=max_per_source)
            print(f"   ✅ Moneycontrol: {len(mc_items)} items")
            
            for item in mc_items:
                all_items.append({
                    "headline": item["headline"],
                    "link": item.get("link", ""),
                    "source_name": "Moneycontrol",
                    "published_at": datetime.utcnow(),
                    "category": item.get("category", "market_news"),
                    "raw_body": "",
                    "ticker": item.get("ticker", "MARKET"),
                })
        except Exception as e:
            print(f"   ❌ Moneycontrol fetch failed: {e}")
    
    # 3. SEBI RSS
    if include_sebi:
        try:
            from sebi_rss import SEBIRSSParser
            print(f"📡 Fetching SEBI circulars...")
            sebi = SEBIRSSParser()
            sebi_items = sebi.fetch_circulars(limit=max_per_source)
            print(f"   ✅ SEBI: {len(sebi_items)} items")
            
            for item in sebi_items:
                all_items.append({
                    "headline": item["headline"],
                    "link": item.get("link", ""),
                    "source_name": "SEBI",
                    "published_at": datetime.fromisoformat(item["timestamp"]) if isinstance(item["timestamp"], str) else item["timestamp"],
                    "category": "regulatory",
                    "raw_body": item.get("raw_body", ""),
                    "ticker": "MARKET",
                })
        except Exception as e:
            print(f"   ❌ SEBI fetch failed: {e}")
    
    print(f"\n📊 Total collected: {len(all_items)} items from all sources")
    return all_items


async def store_and_analyze(items: List[Dict[str, Any]], run_analysis: bool = True):
    """
    Store items in database and optionally run FinBERT analysis.
    """
    from storage.database import async_session_maker, init_db
    from storage.models import NewsItem
    from sqlalchemy import select
    
    # Import ticker extractor
    try:
        from services.ticker_extractor import get_primary_ticker
        has_ticker_extractor = True
    except ImportError:
        has_ticker_extractor = False
    
    await init_db()
    
    # Dedupe within batch
    seen = set()
    unique_items = []
    for item in items:
        key = (item["headline"], item.get("link", ""))
        if key not in seen:
            seen.add(key)
            unique_items.append(item)
    
    print(f"📋 After dedupe: {len(unique_items)} unique items")
    
    new_count = 0
    dup_count = 0
    
    for item in unique_items:
        async with async_session_maker() as session:
            try:
                # Check for existing
                existing = await session.execute(
                    select(NewsItem).where(NewsItem.headline == item["headline"])
                )
                if existing.scalar_one_or_none():
                    dup_count += 1
                    continue
                
                # Extract ticker from headline if not already set
                ticker = item.get("ticker", "MARKET")
                if ticker == "MARKET" and has_ticker_extractor:
                    extracted = get_primary_ticker(item["headline"])
                    if extracted:
                        ticker = extracted
                
                # Insert
                news_item = NewsItem(
                    id=uuid.uuid4(),
                    ticker=ticker,
                    headline=item["headline"],
                    source_url=item.get("link", ""),
                    source_name=item["source_name"],
                    published_at=item["published_at"],
                    category=item.get("category"),
                    raw_body=item.get("raw_body", ""),
                    is_processed=False,
                )
                session.add(news_item)
                await session.commit()
                new_count += 1
                
            except Exception as e:
                print(f"   ⚠️ Error storing: {str(e)[:50]}")
    
    print(f"\n📊 RESULTS:")
    print(f"   New inserted: {new_count}")
    print(f"   Duplicates skipped: {dup_count}")
    
    # Run FinBERT analysis on new items
    if run_analysis and new_count > 0:
        print(f"\n🧠 Running FinBERT analysis on {new_count} new items...")
        try:
            from services.ai_service import MarketAnalyst
            analyst = MarketAnalyst(mock_mode=False, ai_mode="finbert")
            
            async with async_session_maker() as session:
                unprocessed = await session.execute(
                    select(NewsItem).where(NewsItem.is_processed == False)
                )
                items_to_analyze = unprocessed.scalars().all()
                
                for item in items_to_analyze:
                    result = analyst.analyze_text(
                        headline=item.headline,
                        text=item.raw_body,
                        ticker=item.ticker or "MARKET"
                    )
                    
                    item.ai_analysis = result.to_dict()
                    item.sentiment_score = 0.75 if result.sentiment == "Bullish" else (-0.75 if result.sentiment == "Bearish" else 0.0)
                    item.impact_score = float(result.relevance_score)
                    item.is_processed = True
                    
                    if result.relevance_score >= 9:
                        item.priority = "critical"
                    elif result.relevance_score >= 7:
                        item.priority = "high"
                    elif result.relevance_score >= 5:
                        item.priority = "medium"
                    else:
                        item.priority = "low"
                    
                    emoji = "🟢" if result.sentiment == "Bullish" else "🔴" if result.sentiment == "Bearish" else "⚪"
                    print(f"   {emoji} {result.relevance_score}/10 | {item.headline[:50]}...")
                
                await session.commit()
                print(f"   ✅ Analyzed {len(items_to_analyze)} items")
                
        except Exception as e:
            print(f"   ❌ Analysis failed: {e}")
    
    print(f"\n🎉 Done! Refresh your frontend to see the news.")


async def main():
    print("=" * 60)
    print("📰 Multi-Source News Fetcher")
    print("=" * 60)
    
    # Fetch from all sources
    items = await fetch_all_sources(
        include_et=True,
        include_mc=True,
        include_sebi=True,
        max_per_source=20
    )
    
    # Store and analyze
    await store_and_analyze(items, run_analysis=True)


if __name__ == "__main__":
    asyncio.run(main())
