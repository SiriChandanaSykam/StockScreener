"""
Celery Worker Configuration and Tasks.
FIXED: Uses absolute imports to prevent Windows execution errors.
FIXED: Connects to real AI instead of Mock Mode.
"""

import os
import asyncio
import uuid
from datetime import timedelta
from celery import Celery
from celery.schedules import crontab
from dotenv import load_dotenv

# Load environment variables (to get MOCK_MODE and keys)
load_dotenv()

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create Celery app
app = Celery(
    "news_engine",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

# Celery configuration
app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    
    # Task result expiration (1 hour)
    result_expires=3600,
    
    # Task retry settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Concurrency
    worker_prefetch_multiplier=1,
    
    # Beat schedule for periodic tasks
    beat_schedule={
        # Fetch BSE announcements every 5 minutes during market hours
        "fetch-bse-market-hours": {
            "task": "news_engine.worker.fetch_market_updates",
            "schedule": crontab(minute="*/5", hour="9-16", day_of_week="1-5"),
            "args": ("BSE", 1),
            "kwargs": {},
        },
        # Fetch BSE announcements every 30 minutes outside market hours
        "fetch-bse-off-hours": {
            "task": "news_engine.worker.fetch_market_updates",
            "schedule": crontab(minute="*/30", hour="0-8,17-23"),
            "args": ("BSE", 1),
            "kwargs": {},
        },
        # Daily full sync at 6 AM
        "daily-full-sync": {
            "task": "news_engine.worker.fetch_market_updates",
            "schedule": crontab(hour=6, minute=0),
            "args": ("BSE", 7),  # Fetch last 7 days
            "kwargs": {},
        },
        # === RSS NEWS FEEDS ===
        # Fetch Moneycontrol + ET every 5 minutes (priority sources)
        "fetch-rss-priority": {
            "task": "news_engine.worker.fetch_rss_news",
            "schedule": timedelta(minutes=5),
            "args": (["Moneycontrol", "Moneycontrol Markets", "Economic Times Markets", "Economic Times Stocks"],),
            "kwargs": {},
        },
        # Fetch secondary sources every 15 minutes
        "fetch-rss-secondary": {
            "task": "news_engine.worker.fetch_rss_news",
            "schedule": timedelta(minutes=15),
            "args": (["Business Standard Markets", "LiveMint Markets", "Reuters India Business"],),
            "kwargs": {},
        },
    },
)


def run_async(coro):
    """Helper to run async code in sync context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@app.task(
    bind=True,
    name="news_engine.worker.fetch_market_updates",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def fetch_market_updates(self, source: str = "BSE", days_back: int = 1):
    """
    Celery task to fetch market updates from specified source.
    """
    # FIXED: Absolute import (No dot at the start)
    from services.ingest_service import IngestResult

    print(f"🔄 Starting fetch_market_updates: source={source}, days_back={days_back}")
    
    async def _fetch_and_ingest() -> IngestResult:
        if source == "BSE":
            # FIXED: Absolute import (No dot at the start)
            from services.ingest_service import ingest_from_bse
            return await ingest_from_bse(days_back=days_back)
        else:
            raise ValueError(f"Unknown source: {source}")
    
    try:
        result = run_async(_fetch_and_ingest())
        
        summary = {
            "source": source,
            "days_back": days_back,
            "total_received": result.total_received,
            "new_inserted": result.new_inserted,
            "duplicates_skipped": result.duplicates_skipped,
            "errors": result.errors,
            "success_rate": result.success_rate,
        }
        
        print(f"✅ fetch_market_updates complete: {summary}")
        return summary
        
    except Exception as e:
        print(f"❌ fetch_market_updates failed: {e}")
        raise


@app.task(
    bind=True,
    name="news_engine.worker.fetch_rss_news",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def fetch_rss_news(self, sources: list = None):
    """
    Celery task to fetch real-time news from RSS feeds.
    Sources: Moneycontrol, Economic Times, Business Standard, etc.
    """
    from typing import List
    
    print(f"📡 Starting fetch_rss_news: sources={sources or 'all'}")
    
    async def _fetch_rss():
        from ingestors.rss_scraper import fetch_latest_news, RSSNewsItem
        from storage.database import async_session_maker
        from storage.models import NewsItem
        from sqlalchemy import select
        import uuid
        
        # Fetch from RSS feeds
        rss_items: List[RSSNewsItem] = await fetch_latest_news(sources=sources, max_items=100)
        
        if not rss_items:
            return {"total_received": 0, "new_inserted": 0, "duplicates_skipped": 0}
        
        # FIRST: Dedupe within the batch itself (multiple feeds may have same URLs)
        seen_urls = set()
        unique_items = []
        for item in rss_items:
            if item.link not in seen_urls:
                seen_urls.add(item.link)
                unique_items.append(item)
        
        batch_dups = len(rss_items) - len(unique_items)
        print(f"📋 Deduped batch: {len(rss_items)} -> {len(unique_items)} (removed {batch_dups} duplicates)")
        
        new_count = 0
        dup_count = batch_dups  # Start with batch duplicates
        
        async with async_session_maker() as session:
            for rss_item in unique_items:
                # Check for duplicate by URL in DB
                existing = await session.execute(
                    select(NewsItem).where(NewsItem.source_url == rss_item.link)
                )
                if existing.scalar_one_or_none():
                    dup_count += 1
                    continue
                
                # Check for duplicate by headline in DB
                existing_headline = await session.execute(
                    select(NewsItem).where(NewsItem.headline == rss_item.title)
                )
                if existing_headline.scalar_one_or_none():
                    dup_count += 1
                    continue
                
                # Create new NewsItem
                news_item = NewsItem(
                    id=uuid.uuid4(),
                    ticker="MARKET",  # General market news, AI will extract tickers
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
                new_count += 1
                
                # Queue AI analysis (commented out for now to avoid Redis dependency)
                # analyze_news_item.delay(str(news_item.id))
            
            await session.commit()
        
        return {
            "total_received": len(rss_items),
            "new_inserted": new_count,
            "duplicates_skipped": dup_count,
            "sources": sources or "all",
        }
    
    try:
        result = run_async(_fetch_rss())
        print(f"✅ fetch_rss_news complete: {result}")
        return result
    except Exception as e:
        print(f"❌ fetch_rss_news failed: {e}")
        raise


@app.task(
    bind=True,
    name="news_engine.worker.analyze_news_item",
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
    rate_limit="30/m",  # Max 30 API calls per minute
)
def analyze_news_item(self, news_id: str):
    """
    Celery task to analyze a single news item using AI.
    """
    print(f"🧠 Starting AI analysis for news_id: {news_id}")
    
    async def _analyze():
        from sqlalchemy import select
        # FIXED: Absolute imports (No dots)
        from storage.database import async_session_maker
        from storage.models import NewsItem
        from services.ai_service import MarketAnalyst
        
        async with async_session_maker() as session:
            # Fetch the news item
            if isinstance(news_id, str):
                item_uuid = uuid.UUID(news_id)
            else:
                item_uuid = news_id
                
            query = select(NewsItem).where(NewsItem.id == item_uuid)
            result = await session.execute(query)
            news_item = result.scalar_one_or_none()
            
            if not news_item:
                print(f"⚠️ News item not found: {news_id}")
                return {"error": "News item not found", "news_id": str(news_id)}
            
            # Skip if already processed
            if news_item.is_processed:
                print(f"⏭️ Already processed: {news_id}")
                return {"status": "already_processed", "news_id": str(news_id)}
            
            # Analyze with AI
            # FIXED: Checks .env for MOCK_MODE. If not set, defaults to False (Real AI)
            is_mock = os.getenv("MOCK_MODE", "False").lower() == "true"
            analyst = MarketAnalyst(mock_mode=is_mock)
            
            analysis = analyst.analyze_text(
                headline=news_item.headline,
                text=news_item.raw_body,
                ticker=news_item.ticker,
            )
            
            # Update the database record
            news_item.ai_analysis = analysis.to_dict()
            news_item.sentiment_score = _sentiment_to_score(analysis.sentiment)
            news_item.impact_score = float(analysis.relevance_score)
            news_item.priority = _score_to_priority(analysis.relevance_score)
            news_item.is_processed = True
            
            await session.commit()
            
            print(f"✅ Analysis complete for {news_item.ticker}: "
                  f"Score={analysis.relevance_score}, Sentiment={analysis.sentiment}")
            
            return {
                "news_id": str(news_id),
                "ticker": news_item.ticker,
                "relevance_score": analysis.relevance_score,
                "sentiment": analysis.sentiment,
                "summary": analysis.summary,
                "priority": news_item.priority,
            }
    
    try:
        return run_async(_analyze())
    except Exception as e:
        print(f"❌ analyze_news_item failed for {news_id}: {e}")
        raise


def _sentiment_to_score(sentiment: str) -> float:
    """Convert sentiment string to numeric score (-1 to 1)."""
    mapping = {
        "Bullish": 0.75,
        "Bearish": -0.75,
        "Neutral": 0.0,
    }
    return mapping.get(sentiment, 0.0)


def _score_to_priority(relevance_score: int) -> str:
    """Convert relevance score to priority level."""
    if relevance_score >= 9:
        return "critical"
    elif relevance_score >= 7:
        return "high"
    elif relevance_score >= 5:
        return "medium"
    elif relevance_score >= 3:
        return "low"
    else:
        return "noise"


@app.task(name="news_engine.worker.health_check")
def health_check():
    """Simple health check task."""
    return {"status": "healthy", "worker": "news_engine"}


# =============================================================================
# Standalone execution (without Celery)
# =============================================================================

async def run_fetch_once(source: str = "BSE", days_back: int = 1):
    # FIXED: Absolute imports
    from storage.database import init_db
    from services.ingest_service import ingest_from_bse
    
    # Initialize database
    await init_db()
    
    # Fetch and ingest
    if source == "BSE":
        result = await ingest_from_bse(days_back=days_back)
    else:
        raise ValueError(f"Unknown source: {source}")
    
    print(f"\n📊 Results:")
    print(f"   Total received: {result.total_received}")
    print(f"   New inserted: {result.new_inserted}")
    print(f"   Duplicates: {result.duplicates_skipped}")
    print(f"   Errors: {result.errors}")
    
    return result


async def run_analyze_one(news_id: str):
    # FIXED: Absolute imports
    from storage.database import init_db
    
    await init_db()
    
    # Call the task synchronously
    result = analyze_news_item(news_id)
    print(f"\n📊 Analysis Result: {result}")
    return result


if __name__ == "__main__":
    # Run once for testing
    import asyncio
    asyncio.run(run_fetch_once())