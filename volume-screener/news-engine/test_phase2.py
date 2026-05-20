"""
Test script for Phase 2: Persistence Layer.

Run this to verify database setup and ingest service work correctly.
"""

import asyncio
import sys
from pathlib import Path

# Add news-engine to path
sys.path.insert(0, str(Path(__file__).parent))


async def test_phase2():
    """Test database and ingest service."""
    print("=" * 60)
    print("Phase 2 Test: Persistence Layer & Deduplication")
    print("=" * 60)
    
    # Step 1: Initialize database
    print("\n📦 Step 1: Initializing database...")
    from storage.database import init_db, engine
    await init_db()
    print("✅ Database initialized")
    
    # Step 2: Test with mock data
    print("\n📥 Step 2: Testing ingest with mock data...")
    from services.ingest_service import process_incoming_news
    
    mock_news = [
        {
            "Time": "2026-01-12T10:30:00",
            "Ticker": "500325",
            "Company": "Reliance Industries Limited",
            "Title": "Outcome of Board Meeting - Q3 Results",
            "PDF_Link": "https://example.com/reliance_q3_results.pdf",
            "Category": "financial_results",
        },
        {
            "Time": "2026-01-12T11:00:00",
            "Ticker": "532540",
            "Company": "Tata Consultancy Services Limited",
            "Title": "Dividend Declaration - Interim Dividend",
            "PDF_Link": "https://example.com/tcs_dividend.pdf",
            "Category": "dividend",
        },
        {
            "Time": "2026-01-12T11:30:00",
            "Ticker": "500180",
            "Company": "HDFC Bank Limited",
            "Title": "Acquisition of Subsidiary",
            "PDF_Link": "https://example.com/hdfc_acquisition.pdf",
            "Category": "acquisition",
        },
    ]
    
    # First ingest - all should be new
    print("\n🔄 First ingest (all new)...")
    result1 = await process_incoming_news(mock_news, source_name="TEST")
    print(f"   Total: {result1.total_received}")
    print(f"   New: {result1.new_inserted}")
    print(f"   Duplicates: {result1.duplicates_skipped}")
    print(f"   Errors: {result1.errors}")
    
    assert result1.new_inserted == 3, f"Expected 3 new, got {result1.new_inserted}"
    print("✅ First ingest passed!")
    
    # Second ingest - same data, all should be duplicates
    print("\n🔄 Second ingest (all duplicates)...")
    result2 = await process_incoming_news(mock_news, source_name="TEST")
    print(f"   Total: {result2.total_received}")
    print(f"   New: {result2.new_inserted}")
    print(f"   Duplicates: {result2.duplicates_skipped}")
    print(f"   Errors: {result2.errors}")
    
    assert result2.duplicates_skipped == 3, f"Expected 3 duplicates, got {result2.duplicates_skipped}"
    print("✅ Deduplication working correctly!")
    
    # Step 3: Query the database
    print("\n📊 Step 3: Querying database...")
    from storage.database import async_session_maker
    from storage.models import NewsItem
    from sqlalchemy import select
    
    async with async_session_maker() as session:
        query = select(NewsItem).order_by(NewsItem.published_at.desc())
        result = await session.execute(query)
        items = result.scalars().all()
        
        print(f"   Found {len(items)} items in database:")
        for item in items:
            print(f"   - [{item.ticker}] {item.headline[:40]}... ({item.category})")
    
    print("\n" + "=" * 60)
    print("✅ All Phase 2 tests passed!")
    print("=" * 60)
    
    # Cleanup
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(test_phase2())
