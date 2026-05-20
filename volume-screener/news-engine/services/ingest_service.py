"""
Smart Ingest Service with Deduplication.

Handles incoming news from scrapers, checks for duplicates,
and persists only new items to the database.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

# Handle both module and standalone imports
try:
    from ..storage.database import async_session_maker
    from ..storage.models import NewsItem
except ImportError:
    from storage.database import async_session_maker
    from storage.models import NewsItem


# Setup logging
logger = logging.getLogger(__name__)


@dataclass
class IngestResult:
    """Result of an ingest operation."""
    total_received: int
    new_inserted: int
    duplicates_skipped: int
    errors: int
    error_messages: List[str]
    
    @property
    def success_rate(self) -> float:
        if self.total_received == 0:
            return 0.0
        return (self.new_inserted / self.total_received) * 100


async def check_duplicate(
    session: AsyncSession,
    source_url: Optional[str],
    headline: str,
    published_at: datetime,
    ticker: str,
) -> bool:
    """
    Check if a news item already exists in the database.
    
    Deduplication strategy:
    1. Primary: Check by source_url (unique PDF/attachment link)
    2. Fallback: Check by headline + published_at + ticker
    
    Args:
        session: Async database session
        source_url: PDF/attachment URL (may be None)
        headline: News headline
        published_at: Publication timestamp
        ticker: Stock ticker
        
    Returns:
        True if duplicate exists, False otherwise
    """
    conditions = []
    
    # Primary check: source_url (most reliable)
    if source_url:
        conditions.append(NewsItem.source_url == source_url)
    
    # Fallback check: headline + published_at + ticker
    conditions.append(
        (NewsItem.headline == headline) & 
        (NewsItem.published_at == published_at) &
        (NewsItem.ticker == ticker)
    )
    
    query = select(NewsItem.id).where(or_(*conditions)).limit(1)
    result = await session.execute(query)
    
    return result.scalar() is not None


async def insert_news_item(
    session: AsyncSession,
    news_data: Dict[str, Any],
) -> Optional[NewsItem]:
    """
    Insert a single news item into the database.
    
    Args:
        session: Async database session
        news_data: Dictionary with news fields
        
    Returns:
        NewsItem if inserted, None if duplicate or error
    """
    try:
        news_item = NewsItem(
            ticker=news_data.get("ticker", ""),
            company_name=news_data.get("company_name"),
            headline=news_data.get("headline", ""),
            raw_body=news_data.get("raw_body"),
            source_url=news_data.get("source_url"),
            source_name=news_data.get("source_name", "BSE"),
            published_at=news_data.get("published_at", datetime.utcnow()),
            category=news_data.get("category"),
            priority=news_data.get("priority"),
            raw_data=news_data.get("raw_data"),
        )
        
        session.add(news_item)
        await session.flush()  # Get the ID without committing
        
        return news_item
        
    except IntegrityError as e:
        # Duplicate detected via database constraint
        await session.rollback()
        logger.debug(f"Duplicate detected via constraint: {news_data.get('headline', '')[:50]}")
        return None
    except Exception as e:
        await session.rollback()
        logger.error(f"Error inserting news item: {e}")
        raise


async def process_incoming_news(
    news_list: List[Dict[str, Any]],
    source_name: str = "BSE",
) -> IngestResult:
    """
    Process incoming news from scrapers with deduplication.
    
    This function:
    1. Receives raw news data from scrapers
    2. Checks each item against the database for duplicates
    3. Inserts only new items
    4. Returns detailed statistics
    
    Args:
        news_list: List of news items from scraper
            Expected format (from BSE scraper):
            {
                "Time": "2026-01-12T10:30:00",
                "Ticker": "500325",
                "Company": "Reliance Industries",
                "Title": "Board Meeting Outcome",
                "PDF_Link": "https://...",
                "Category": "board_meeting",
            }
        source_name: Name of the source (BSE, NSE, etc.)
        
    Returns:
        IngestResult with counts of inserted, skipped, and errors
    """
    result = IngestResult(
        total_received=len(news_list),
        new_inserted=0,
        duplicates_skipped=0,
        errors=0,
        error_messages=[],
    )
    
    if not news_list:
        logger.info("No news items to process")
        return result
    
    async with async_session_maker() as session:
        for raw_news in news_list:
            try:
                # Normalize field names from different scraper formats
                ticker = raw_news.get("Ticker") or raw_news.get("ticker", "")
                headline = raw_news.get("Title") or raw_news.get("headline", "")
                company = raw_news.get("Company") or raw_news.get("company_name", "")
                source_url = raw_news.get("PDF_Link") or raw_news.get("source_url")
                category = raw_news.get("Category") or raw_news.get("category")
                
                # Parse timestamp
                time_str = raw_news.get("Time") or raw_news.get("published_at")
                if isinstance(time_str, str):
                    try:
                        published_at = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                    except ValueError:
                        published_at = datetime.utcnow()
                elif isinstance(time_str, datetime):
                    published_at = time_str
                else:
                    published_at = datetime.utcnow()
                
                # Skip empty headlines
                if not headline or not ticker:
                    logger.warning(f"Skipping item with empty headline or ticker: {raw_news}")
                    result.errors += 1
                    result.error_messages.append("Empty headline or ticker")
                    continue
                
                # Check for duplicates
                is_duplicate = await check_duplicate(
                    session=session,
                    source_url=source_url,
                    headline=headline,
                    published_at=published_at,
                    ticker=ticker,
                )
                
                if is_duplicate:
                    result.duplicates_skipped += 1
                    logger.debug(f"Skipping duplicate: {headline[:50]}...")
                    continue
                
                # Prepare normalized data
                news_data = {
                    "ticker": ticker,
                    "company_name": company,
                    "headline": headline,
                    "source_url": source_url,
                    "source_name": source_name,
                    "published_at": published_at,
                    "category": category,
                    "raw_data": raw_news,
                }
                
                # Insert new item
                news_item = await insert_news_item(session, news_data)
                
                if news_item:
                    result.new_inserted += 1
                    logger.info(f"✅ Inserted: [{ticker}] {headline[:50]}...")
                    
                    # Trigger AI analysis task (event-driven)
                    try:
                        from ..worker import analyze_news_item
                        analyze_news_item.delay(str(news_item.id))
                        logger.info(f"🧠 Queued AI analysis for: {news_item.id}")
                    except ImportError:
                        # Celery not available (standalone mode)
                        logger.debug("Celery not available, skipping async analysis")
                    except Exception as e:
                        # Don't fail the ingest if analysis queue fails
                        logger.warning(f"Failed to queue analysis: {e}")
                else:
                    result.duplicates_skipped += 1
                    
            except Exception as e:
                result.errors += 1
                error_msg = f"Error processing item: {str(e)}"
                result.error_messages.append(error_msg)
                logger.error(error_msg)
        
        # Commit all successful inserts
        try:
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Error committing transaction: {e}")
            result.errors += result.new_inserted
            result.new_inserted = 0
            result.error_messages.append(f"Commit failed: {str(e)}")
    
    # Log summary
    logger.info(
        f"📊 Ingest complete: {result.new_inserted} new, "
        f"{result.duplicates_skipped} duplicates, "
        f"{result.errors} errors out of {result.total_received} total"
    )
    
    return result


# Convenience function for quick testing
async def ingest_from_bse(days_back: int = 1) -> IngestResult:
    """
    Fetch from BSE scraper and ingest into database.
    
    Args:
        days_back: Number of days to fetch
        
    Returns:
        IngestResult with statistics
    """
    from ..ingestors.bse_scraper import fetch_bse_announcements
    
    # Fetch from BSE
    news_list = await fetch_bse_announcements(days_back=days_back)
    
    # Process and store
    return await process_incoming_news(news_list, source_name="BSE")
