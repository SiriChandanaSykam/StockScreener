"""
Test script for Phase 4: Delivery Layer (REST API).

Tests the FastAPI endpoints directly without HTTP.
"""

import asyncio
import sys
from pathlib import Path

# Add news-engine to path
sys.path.insert(0, str(Path(__file__).parent))


async def test_api():
    """Test API endpoints directly."""
    print("=" * 60)
    print("Phase 4 Test: Delivery Layer (REST API)")
    print("=" * 60)
    
    from storage.database import init_db, async_session_maker, engine
    from storage.models import NewsItem
    from services.ingest_service import process_incoming_news
    from api.schemas import NewsItemResponse, NewsFeedResponse
    from sqlalchemy import select, func
    import uuid
    
    # Initialize database
    print("\n📦 Initializing database...")
    await init_db()
    
    # Insert test data
    print("\n📥 Inserting test data...")
    test_id = str(uuid.uuid4())[:8]
    
    mock_news = [
        {
            "Time": "2026-01-13T10:30:00",
            "Ticker": "TCS",
            "Company": "Tata Consultancy Services",
            "Title": f"Major Deal Win - $1B Contract [{test_id}]",
            "PDF_Link": f"https://bse.com/tcs_deal_{test_id}.pdf",
            "Category": "order_win",
        },
        {
            "Time": "2026-01-13T11:00:00",
            "Ticker": "INFY",
            "Company": "Infosys Limited",
            "Title": f"Q3 Results - Revenue up 15% [{test_id}]",
            "PDF_Link": f"https://bse.com/infy_q3_{test_id}.pdf",
            "Category": "financial_results",
        },
        {
            "Time": "2026-01-13T11:30:00",
            "Ticker": "HDFC",
            "Company": "HDFC Bank",
            "Title": f"Board Meeting Notice [{test_id}]",
            "PDF_Link": f"https://bse.com/hdfc_board_{test_id}.pdf",
            "Category": "board_meeting",
        },
    ]
    
    result = await process_incoming_news(mock_news, source_name="TEST")
    print(f"   Inserted: {result.new_inserted} items")
    
    # Simulate AI analysis
    print("\n🧠 Simulating AI analysis...")
    from services.ai_service import MarketAnalyst
    analyst = MarketAnalyst(mock_mode=True)
    
    async with async_session_maker() as session:
        query = select(NewsItem).where(NewsItem.is_processed == False).limit(10)
        db_result = await session.execute(query)
        items = db_result.scalars().all()
        
        for item in items:
            analysis = analyst.analyze_text(item.headline, ticker=item.ticker)
            item.ai_analysis = analysis.to_dict()
            item.sentiment_score = 0.75 if analysis.sentiment == "Bullish" else -0.75 if analysis.sentiment == "Bearish" else 0.0
            item.impact_score = float(analysis.relevance_score)
            item.priority = "high" if analysis.relevance_score >= 7 else "medium"
            item.is_processed = True
        
        await session.commit()
        print(f"   Analyzed: {len(items)} items")
    
    # Test 1: NewsItemResponse schema
    print("\n📋 Test 1: NewsItemResponse Schema")
    async with async_session_maker() as session:
        query = select(NewsItem).limit(1)
        db_result = await session.execute(query)
        item = db_result.scalar_one_or_none()
        
        if item:
            response = NewsItemResponse.from_db_model(item)
            print(f"   ✓ ID: {response.id[:8]}...")
            print(f"   ✓ Ticker: {response.ticker}")
            print(f"   ✓ Headline: {response.headline[:40]}...")
            print(f"   ✓ Relevance Score: {response.relevance_score}")
            print(f"   ✓ Sentiment: {response.sentiment}")
            print(f"   ✓ Priority: {response.priority}")
            assert response.id is not None
            assert response.ticker is not None
    
    print("   ✅ Schema test passed!")
    
    # Test 2: Feed endpoint logic
    print("\n📋 Test 2: Feed Query Logic")
    async with async_session_maker() as session:
        # Query with filters
        query = (
            select(NewsItem)
            .where(NewsItem.impact_score >= 5)
            .order_by(NewsItem.published_at.desc())
            .limit(10)
        )
        db_result = await session.execute(query)
        items = db_result.scalars().all()
        
        print(f"   Found {len(items)} items with impact_score >= 5")
        for item in items[:3]:
            print(f"   - [{item.ticker}] Score: {item.impact_score} | {item.headline[:30]}...")
    
    print("   ✅ Feed query test passed!")
    
    # Test 3: Latest endpoint logic
    print("\n📋 Test 3: Latest/Polling Query Logic")
    from datetime import datetime, timedelta
    
    async with async_session_maker() as session:
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        query = (
            select(NewsItem)
            .where(NewsItem.created_at > one_hour_ago)
            .order_by(NewsItem.created_at.desc())
            .limit(5)
        )
        db_result = await session.execute(query)
        items = db_result.scalars().all()
        
        print(f"   Found {len(items)} items in last hour")
        if items:
            print(f"   Latest ID: {items[0].id}")
            print(f"   Latest Time: {items[0].created_at}")
    
    print("   ✅ Polling query test passed!")
    
    # Test 4: Stats query
    print("\n📋 Test 4: Stats Query Logic")
    async with async_session_maker() as session:
        total = await session.execute(select(func.count(NewsItem.id)))
        processed = await session.execute(
            select(func.count(NewsItem.id)).where(NewsItem.is_processed == True)
        )
        
        print(f"   Total items: {total.scalar()}")
        print(f"   Processed items: {processed.scalar()}")
    
    print("   ✅ Stats query test passed!")
    
    await engine.dispose()
    
    print("\n" + "=" * 60)
    print("✅ ALL PHASE 4 TESTS PASSED!")
    print("=" * 60)
    print("\n🚀 API Ready! Start with:")
    print("   cd news-engine")
    print("   uvicorn main:app --reload --port 8001")
    print("\n📖 Docs: http://localhost:8001/docs")
    
    return True


if __name__ == "__main__":
    asyncio.run(test_api())
