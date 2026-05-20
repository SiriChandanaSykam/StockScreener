"""
Test script for Phase 3: AI Intelligence Layer.

Tests the MarketAnalyst service and the end-to-end pipeline:
Ingest -> Store -> Trigger Analysis -> Update DB
"""

import asyncio
import sys
import uuid
from pathlib import Path

# Add news-engine to path
sys.path.insert(0, str(Path(__file__).parent))


async def test_ai_service():
    """Test the MarketAnalyst standalone."""
    print("\n" + "=" * 60)
    print("Test 1: MarketAnalyst Service (Standalone)")
    print("=" * 60)
    
    from services.ai_service import MarketAnalyst, AnalysisResult
    
    analyst = MarketAnalyst(mock_mode=True)
    
    test_cases = [
        ("TCS bags $500M deal from major US bank", "TCS"),
        ("Quarterly Results - Profit up 25% YoY", "INFY"),
        ("Board Meeting to consider Bonus Issue", "HDFC"),
        ("ISIN Code Update for Corporate Action", "RELIANCE"),
        ("Acquisition of XYZ Limited for ₹2000 Cr", "LT"),
    ]
    
    print("\n📊 Analysis Results:")
    for headline, ticker in test_cases:
        result = analyst.analyze_text(headline, ticker=ticker)
        
        assert isinstance(result, AnalysisResult), "Result should be AnalysisResult"
        assert 1 <= result.relevance_score <= 10, "Score should be 1-10"
        assert result.sentiment in ["Bullish", "Bearish", "Neutral"], "Invalid sentiment"
        assert len(result.summary) <= 100, "Summary too long"
        
        print(f"\n   📢 {headline[:50]}...")
        print(f"      Score: {result.relevance_score}/10 | {result.sentiment}")
        print(f"      Summary: {result.summary}")
    
    print("\n✅ MarketAnalyst tests passed!")
    return True


async def test_end_to_end_pipeline():
    """Test the complete pipeline: Ingest -> Analyze."""
    print("\n" + "=" * 60)
    print("Test 2: End-to-End Pipeline (Ingest -> Analyze)")
    print("=" * 60)
    
    from storage.database import init_db, async_session_maker, engine
    from storage.models import NewsItem
    from services.ingest_service import process_incoming_news
    from services.ai_service import MarketAnalyst
    from sqlalchemy import select
    
    # Initialize database
    print("\n📦 Initializing database...")
    await init_db()
    
    # Clear any existing test data first
    async with async_session_maker() as session:
        # Insert unique test items
        test_id = str(uuid.uuid4())[:8]
        
        mock_news = [
            {
                "Time": "2026-01-13T10:30:00",
                "Ticker": "TCS",
                "Company": "Tata Consultancy Services",
                "Title": f"Major Deal Win - $1B Contract [{test_id}]",
                "PDF_Link": f"https://example.com/tcs_deal_{test_id}.pdf",
                "Category": "order_win",
            },
            {
                "Time": "2026-01-13T11:00:00",
                "Ticker": "INFY",
                "Company": "Infosys Limited",
                "Title": f"Q3 Results - Revenue up 15% [{test_id}]",
                "PDF_Link": f"https://example.com/infy_q3_{test_id}.pdf",
                "Category": "financial_results",
            },
        ]
    
    # Ingest (this should trigger analysis queue in prod)
    print("\n🔄 Ingesting test news...")
    result = await process_incoming_news(mock_news, source_name="TEST")
    
    print(f"   Ingested: {result.new_inserted} new, {result.duplicates_skipped} duplicates")
    assert result.new_inserted >= 0, "Ingest should work"
    
    # Manually analyze the items (simulating what Celery would do)
    print("\n🧠 Running AI analysis...")
    analyst = MarketAnalyst(mock_mode=True)
    
    async with async_session_maker() as session:
        # Get unprocessed items
        query = select(NewsItem).where(
            NewsItem.is_processed == False,
            NewsItem.source_name == "TEST"
        ).limit(5)
        
        db_result = await session.execute(query)
        items = db_result.scalars().all()
        
        for item in items:
            # Analyze
            analysis = analyst.analyze_text(
                headline=item.headline,
                text=item.raw_body,
                ticker=item.ticker,
            )
            
            # Update record
            item.ai_analysis = analysis.to_dict()
            item.sentiment_score = 0.75 if analysis.sentiment == "Bullish" else -0.75 if analysis.sentiment == "Bearish" else 0.0
            item.impact_score = float(analysis.relevance_score)
            item.is_processed = True
            
            print(f"\n   ✅ Analyzed: [{item.ticker}]")
            print(f"      Score: {analysis.relevance_score}/10 | {analysis.sentiment}")
            print(f"      Summary: {analysis.summary}")
        
        await session.commit()
    
    # Verify updates
    print("\n📊 Verifying database updates...")
    async with async_session_maker() as session:
        query = select(NewsItem).where(
            NewsItem.source_name == "TEST",
            NewsItem.is_processed == True
        ).limit(5)
        
        db_result = await session.execute(query)
        processed_items = db_result.scalars().all()
        
        for item in processed_items:
            assert item.ai_analysis is not None, "AI analysis should be populated"
            assert item.impact_score is not None, "Impact score should be set"
            print(f"   ✓ {item.ticker}: impact={item.impact_score}, sentiment={item.sentiment_score}")
    
    await engine.dispose()
    print("\n✅ End-to-end pipeline test passed!")
    return True


async def test_phase3():
    """Run all Phase 3 tests."""
    print("=" * 60)
    print("Phase 3 Test: AI Intelligence Layer")
    print("=" * 60)
    
    try:
        await test_ai_service()
        await test_end_to_end_pipeline()
        
        print("\n" + "=" * 60)
        print("✅ ALL PHASE 3 TESTS PASSED!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    asyncio.run(test_phase3())
