"""
FastAPI Routes for News Intelligence Engine.

Provides REST endpoints for:
- News feed with filtering and pagination
- Live polling for new items
- Statistics and health checks
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException, Path
from sqlalchemy import select, func, desc, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

# Handle both module and standalone imports
try:
    from ..storage.database import get_session
    from ..storage.models import NewsItem
    from .schemas import (
        NewsItemResponse,
        NewsFeedResponse,
        NewsLatestResponse,
        HealthResponse,
        StatsResponse,
        SentimentEnum,
        PriorityEnum,
    )
except ImportError:
    from storage.database import get_session
    from storage.models import NewsItem
    from api.schemas import (
        NewsItemResponse,
        NewsFeedResponse,
        NewsLatestResponse,
        HealthResponse,
        StatsResponse,
        SentimentEnum,
        PriorityEnum,
    )


# Create router
router = APIRouter(prefix="/news", tags=["News"])


# =============================================================================
# Main Feed Endpoint
# =============================================================================

@router.get("/feed", response_model=NewsFeedResponse)
async def get_news_feed(
    min_relevance: int = Query(default=0, ge=0, le=10, description="Minimum relevance score"),
    ticker: Optional[str] = Query(default=None, description="Filter by ticker"),
    sentiment: Optional[str] = Query(default=None, description="Bullish/Bearish/Neutral"),
    category: Optional[str] = Query(default=None, description="Filter by category"),
    priority: Optional[str] = Query(default=None, description="critical/high/medium/low/noise"),
    source: Optional[str] = Query(default=None, description="Filter by source (BSE, NSE)"),
    processed_only: bool = Query(default=False, description="Only AI-processed items"),
    limit: int = Query(default=50, ge=1, le=200, description="Items per page"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
    session: AsyncSession = Depends(get_session),
):
    """
    Get paginated news feed with filtering.
    
    The main endpoint for displaying news in the frontend.
    Supports filtering by relevance, ticker, sentiment, and more.
    
    **Default Sorting:** Newest first (published_at descending)
    
    **Example:**
    ```
    GET /news/feed?min_relevance=7&ticker=TCS&limit=20
    ```
    """
    # Build base query
    query = select(NewsItem)
    count_query = select(func.count(NewsItem.id))
    
    # Apply filters
    filters = []
    
    if min_relevance > 0:
        filters.append(NewsItem.impact_score >= min_relevance)
    
    if ticker:
        # Case-insensitive ticker match
        filters.append(func.upper(NewsItem.ticker) == ticker.upper())
    
    if sentiment:
        # Sentiment is stored in ai_analysis JSON
        # For SQLite, we check sentiment_score range
        if sentiment.lower() == "bullish":
            filters.append(NewsItem.sentiment_score > 0.3)
        elif sentiment.lower() == "bearish":
            filters.append(NewsItem.sentiment_score < -0.3)
        else:  # neutral
            filters.append(
                and_(
                    NewsItem.sentiment_score >= -0.3,
                    NewsItem.sentiment_score <= 0.3
                )
            )
    
    if category:
        filters.append(NewsItem.category == category.lower())
    
    if priority:
        filters.append(NewsItem.priority == priority.lower())
    
    if source:
        filters.append(func.upper(NewsItem.source_name) == source.upper())
    
    if processed_only:
        filters.append(NewsItem.is_processed == True)
    
    # Apply filters to queries
    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))
    
    # Get total count
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply sorting and pagination
    query = (
        query
        .order_by(desc(NewsItem.published_at))
        .limit(limit)
        .offset(offset)
    )
    
    # Execute query
    result = await session.execute(query)
    items = result.scalars().all()
    
    # Convert to response models
    response_items = [NewsItemResponse.from_db_model(item) for item in items]
    
    return NewsFeedResponse(
        items=response_items,
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + len(items)) < total,
    )


# =============================================================================
# Live Polling Endpoint
# =============================================================================

@router.get("/latest", response_model=NewsLatestResponse)
async def get_latest_news(
    since_id: Optional[str] = Query(default=None, description="Return items after this ID"),
    since_timestamp: Optional[datetime] = Query(default=None, description="Return items after this time"),
    min_relevance: int = Query(default=0, ge=0, le=10, description="Minimum relevance score"),
    ticker: Optional[str] = Query(default=None, description="Filter by ticker"),
    limit: int = Query(default=20, ge=1, le=100, description="Max items to return"),
    session: AsyncSession = Depends(get_session),
):
    """
    Get latest news items for live polling.
    
    Use this endpoint for the "Live Alerts" feature in the frontend.
    Poll every 30-60 seconds with the `since_id` or `since_timestamp`
    from the previous response.
    
    **Example:**
    ```
    # First request
    GET /news/latest?min_relevance=7
    
    # Subsequent requests (use latest_id from previous response)
    GET /news/latest?since_id=abc123&min_relevance=7
    ```
    """
    query = select(NewsItem)
    filters = []
    
    # Filter by since_id (items created after the given ID)
    if since_id:
        try:
            since_uuid = uuid.UUID(since_id)
            # Get the created_at of the reference item
            ref_query = select(NewsItem.created_at).where(NewsItem.id == since_uuid)
            ref_result = await session.execute(ref_query)
            ref_time = ref_result.scalar()
            
            if ref_time:
                filters.append(NewsItem.created_at > ref_time)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid since_id format")
    
    # Filter by since_timestamp
    elif since_timestamp:
        filters.append(NewsItem.created_at > since_timestamp)
    
    # If neither provided, get items from last hour
    else:
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        filters.append(NewsItem.created_at > one_hour_ago)
    
    # Apply relevance filter
    if min_relevance > 0:
        filters.append(NewsItem.impact_score >= min_relevance)
    
    # Apply ticker filter
    if ticker:
        filters.append(func.upper(NewsItem.ticker) == ticker.upper())
    
    # Apply filters
    if filters:
        query = query.where(and_(*filters))
    
    # Sort by created_at descending (newest first), limit results
    query = (
        query
        .order_by(desc(NewsItem.created_at))
        .limit(limit)
    )
    
    # Execute
    result = await session.execute(query)
    items = result.scalars().all()
    
    # Convert to response
    response_items = [NewsItemResponse.from_db_model(item) for item in items]
    
    # Get latest item info for next poll
    latest_id = str(items[0].id) if items else None
    latest_timestamp = items[0].created_at if items else None
    
    return NewsLatestResponse(
        items=response_items,
        count=len(response_items),
        latest_id=latest_id,
        latest_timestamp=latest_timestamp,
    )


# =============================================================================
# Single Item Endpoint
# =============================================================================

@router.get("/{news_id}", response_model=NewsItemResponse)
async def get_news_item(
    news_id: str = Path(..., description="UUID of the news item"),
    session: AsyncSession = Depends(get_session),
):
    """
    Get a single news item by ID.
    
    **Example:**
    ```
    GET /news/abc123-def456-...
    ```
    """
    try:
        item_uuid = uuid.UUID(news_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid news_id format")
    
    query = select(NewsItem).where(NewsItem.id == item_uuid)
    result = await session.execute(query)
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail="News item not found")
    
    return NewsItemResponse.from_db_model(item)


# =============================================================================
# Statistics Endpoint
# =============================================================================

@router.get("/stats/overview", response_model=StatsResponse)
async def get_stats(
    session: AsyncSession = Depends(get_session),
):
    """
    Get statistics about the news database.
    
    **Example:**
    ```
    GET /news/stats/overview
    ```
    """
    # Total items
    total_result = await session.execute(select(func.count(NewsItem.id)))
    total = total_result.scalar() or 0
    
    # Processed items
    processed_result = await session.execute(
        select(func.count(NewsItem.id)).where(NewsItem.is_processed == True)
    )
    processed = processed_result.scalar() or 0
    
    # Items today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_result = await session.execute(
        select(func.count(NewsItem.id)).where(NewsItem.created_at >= today_start)
    )
    today_count = today_result.scalar() or 0
    
    # Items by source
    source_query = (
        select(NewsItem.source_name, func.count(NewsItem.id))
        .group_by(NewsItem.source_name)
    )
    source_result = await session.execute(source_query)
    items_by_source = {row[0]: row[1] for row in source_result}
    
    # Items by sentiment (approximate based on score)
    bullish_result = await session.execute(
        select(func.count(NewsItem.id)).where(NewsItem.sentiment_score > 0.3)
    )
    bearish_result = await session.execute(
        select(func.count(NewsItem.id)).where(NewsItem.sentiment_score < -0.3)
    )
    neutral_result = await session.execute(
        select(func.count(NewsItem.id)).where(
            and_(
                NewsItem.sentiment_score >= -0.3,
                NewsItem.sentiment_score <= 0.3,
                NewsItem.sentiment_score.isnot(None)
            )
        )
    )
    
    items_by_sentiment = {
        "bullish": bullish_result.scalar() or 0,
        "bearish": bearish_result.scalar() or 0,
        "neutral": neutral_result.scalar() or 0,
    }
    
    return StatsResponse(
        total_items=total,
        processed_items=processed,
        unprocessed_items=total - processed,
        items_today=today_count,
        items_by_source=items_by_source,
        items_by_sentiment=items_by_sentiment,
    )


# =============================================================================
# Tickers Endpoint (for dropdown/autocomplete)
# =============================================================================

@router.get("/tickers/list", response_model=List[str])
async def get_tickers(
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
):
    """
    Get list of unique tickers in the database.
    Useful for filter dropdowns in the frontend.
    """
    query = (
        select(NewsItem.ticker)
        .distinct()
        .order_by(NewsItem.ticker)
        .limit(limit)
    )
    
    result = await session.execute(query)
    tickers = [row[0] for row in result]
    
    return tickers


# =============================================================================
# Watchlist News Endpoint
# =============================================================================

@router.post("/watchlist")
async def get_watchlist_news(
    tickers: List[str],
    min_relevance: int = Query(default=0, ge=0, le=10),
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
):
    """
    Get news for multiple tickers (watchlist).
    
    **Request Body:**
    ```json
    ["RELIANCE", "TCS", "INFY", "HDFC"]
    ```
    
    **Example:**
    ```
    POST /news/watchlist?min_relevance=5&limit=30
    Body: ["RELIANCE", "TCS"]
    ```
    """
    if not tickers:
        raise HTTPException(status_code=400, detail="At least one ticker required")
    
    # Normalize tickers to uppercase
    tickers_upper = [t.upper() for t in tickers]
    
    # Build query for any matching ticker
    query = select(NewsItem).where(
        or_(*[func.upper(NewsItem.ticker) == t for t in tickers_upper])
    )
    
    if min_relevance > 0:
        query = query.where(NewsItem.impact_score >= min_relevance)
    
    query = query.order_by(desc(NewsItem.published_at)).limit(limit)
    
    result = await session.execute(query)
    items = result.scalars().all()
    
    response_items = [NewsItemResponse.from_db_model(item) for item in items]
    
    return {
        "items": response_items,
        "tickers": tickers_upper,
        "count": len(response_items),
    }


# =============================================================================
# High Impact Alerts Endpoint
# =============================================================================

@router.get("/alerts/high-impact")
async def get_high_impact_news(
    hours: int = Query(default=24, ge=1, le=168, description="Look back hours"),
    min_score: int = Query(default=8, ge=1, le=10, description="Minimum impact score"),
    session: AsyncSession = Depends(get_session),
):
    """
    Get high-impact news from the last N hours.
    Perfect for alerts and notifications.
    
    **Example:**
    ```
    GET /news/alerts/high-impact?hours=4&min_score=9
    ```
    """
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    
    query = (
        select(NewsItem)
        .where(
            and_(
                NewsItem.published_at >= cutoff,
                NewsItem.impact_score >= min_score,
            )
        )
        .order_by(desc(NewsItem.impact_score), desc(NewsItem.published_at))
        .limit(50)
    )
    
    result = await session.execute(query)
    items = result.scalars().all()
    
    response_items = [NewsItemResponse.from_db_model(item) for item in items]
    
    # Group by sentiment
    bullish = [i for i in response_items if i.sentiment == "Bullish"]
    bearish = [i for i in response_items if i.sentiment == "Bearish"]
    
    return {
        "items": response_items,
        "summary": {
            "total": len(response_items),
            "bullish": len(bullish),
            "bearish": len(bearish),
            "lookback_hours": hours,
            "min_score": min_score,
        }
    }


# =============================================================================
# News Digest Endpoint
# =============================================================================

@router.get("/digest")
async def get_news_digest(
    hours: int = Query(default=24, ge=1, le=168, description="Look back hours"),
    min_score: int = Query(default=5, ge=1, le=10, description="Minimum score to include"),
    session: AsyncSession = Depends(get_session),
):
    """
    Get a summarized news digest for the period.
    
    **Example:**
    ```
    GET /news/digest?hours=24&min_score=7
    ```
    """
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    
    # Get all items in period
    query = (
        select(NewsItem)
        .where(NewsItem.published_at >= cutoff)
        .order_by(desc(NewsItem.impact_score), desc(NewsItem.published_at))
    )
    
    result = await session.execute(query)
    items = result.scalars().all()
    
    # Calculate stats
    total = len(items)
    high_impact = sum(1 for i in items if (i.impact_score or 0) >= 8)
    bullish = sum(1 for i in items if (i.sentiment_score or 0) > 0.3)
    bearish = sum(1 for i in items if (i.sentiment_score or 0) < -0.3)
    
    # Top items (score >= min_score)
    top_items = [
        NewsItemResponse.from_db_model(i) 
        for i in items 
        if (i.impact_score or 0) >= min_score
    ][:20]
    
    # Group by ticker
    by_ticker = {}
    for item in items:
        ticker = item.ticker or "MARKET"
        if ticker not in by_ticker:
            by_ticker[ticker] = 0
        by_ticker[ticker] += 1
    
    # Sort tickers by count
    top_tickers = sorted(by_ticker.items(), key=lambda x: x[1], reverse=True)[:10]
    
    return {
        "period": {
            "hours": hours,
            "start": cutoff.isoformat(),
            "end": datetime.utcnow().isoformat(),
        },
        "summary": {
            "total": total,
            "high_impact": high_impact,
            "bullish": bullish,
            "bearish": bearish,
            "neutral": total - bullish - bearish,
        },
        "top_items": top_items,
        "top_tickers": [{"ticker": t, "count": c} for t, c in top_tickers],
    }


# =============================================================================
# News Search Endpoint
# =============================================================================

@router.get("/search")
async def search_news(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(default=30, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """
    Search news headlines.
    
    **Example:**
    ```
    GET /news/search?q=reliance profit&limit=20
    ```
    """
    # Search in headline (case-insensitive)
    query = (
        select(NewsItem)
        .where(NewsItem.headline.ilike(f"%{q}%"))
        .order_by(desc(NewsItem.published_at))
        .limit(limit)
    )
    
    result = await session.execute(query)
    items = result.scalars().all()
    
    response_items = [NewsItemResponse.from_db_model(item) for item in items]
    
    return {
        "query": q,
        "count": len(response_items),
        "items": response_items,
    }


# =============================================================================
# Health Check
# =============================================================================

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    """
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow(),
    )
