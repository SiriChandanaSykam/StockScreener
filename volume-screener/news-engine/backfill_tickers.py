"""
Backfill tickers for existing news items.
Updates items with ticker='MARKET' to have proper tickers based on headline.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from storage.database import async_session_maker, init_db
from storage.models import NewsItem
from services.ticker_extractor import get_primary_ticker
from sqlalchemy import select


async def backfill_tickers():
    print("=" * 60)
    print("🔧 Backfill Tickers for Existing News")
    print("=" * 60)
    
    await init_db()
    
    async with async_session_maker() as session:
        # Get all items with MARKET ticker
        result = await session.execute(
            select(NewsItem).where(NewsItem.ticker == "MARKET")
        )
        items = result.scalars().all()
        
        print(f"📰 Found {len(items)} items with 'MARKET' ticker")
        
        updated = 0
        for item in items:
            extracted = get_primary_ticker(item.headline)
            if extracted:
                item.ticker = extracted
                updated += 1
                print(f"   ✅ {item.headline[:40]}... → {extracted}")
        
        await session.commit()
        
        print(f"\n📊 Results:")
        print(f"   Updated: {updated}")
        print(f"   Unchanged: {len(items) - updated}")


if __name__ == "__main__":
    asyncio.run(backfill_tickers())
