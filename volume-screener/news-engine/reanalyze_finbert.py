"""
Re-analyze all news items in database using FinBERT.
This updates existing items with proper AI scores.
"""
import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(__file__))

from storage.database import async_session_maker, init_db
from storage.models import NewsItem
from services.ai_service import MarketAnalyst
from sqlalchemy import select, update


async def reanalyze_all():
    print("=" * 60)
    print("🧠 Re-analyzing all news with FinBERT (FREE, Unlimited)")
    print("=" * 60)
    
    # Init DB
    await init_db()
    
    # Create analyst with FinBERT
    analyst = MarketAnalyst(mock_mode=False, ai_mode="finbert")
    
    if analyst.finbert is None:
        print("❌ FinBERT not available! Run: pip install transformers torch")
        return
    
    print(f"✅ Using: {analyst.ai_mode.upper()}")
    
    async with async_session_maker() as session:
        # Get all items
        query = select(NewsItem)
        result = await session.execute(query)
        items = result.scalars().all()
        
        print(f"📰 Found {len(items)} news items to analyze")
        
        updated = 0
        for i, item in enumerate(items, 1):
            print(f"\n[{i}/{len(items)}] {item.headline[:60]}...")
            
            try:
                analysis = analyst.analyze_text(
                    headline=item.headline,
                    text=item.raw_body,
                    ticker=item.ticker or "MARKET"
                )
                
                # Update item
                item.ai_analysis = analysis.to_dict()
                item.sentiment_score = 0.75 if analysis.sentiment == "Bullish" else (-0.75 if analysis.sentiment == "Bearish" else 0.0)
                item.impact_score = float(analysis.relevance_score)
                item.is_processed = True
                
                # Set priority
                if analysis.relevance_score >= 9:
                    item.priority = "critical"
                elif analysis.relevance_score >= 7:
                    item.priority = "high"
                elif analysis.relevance_score >= 5:
                    item.priority = "medium"
                else:
                    item.priority = "low"
                
                emoji = "🟢" if analysis.sentiment == "Bullish" else "🔴" if analysis.sentiment == "Bearish" else "⚪"
                print(f"   {emoji} Score: {analysis.relevance_score}/10 | {analysis.sentiment} ({analysis.confidence:.0%})")
                
                updated += 1
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        await session.commit()
        
        print("\n" + "=" * 60)
        print(f"✅ Done! Updated {updated}/{len(items)} items with FinBERT analysis")
        print("=" * 60)
        print("\n🔄 Refresh your browser to see the new scores!")


if __name__ == "__main__":
    asyncio.run(reanalyze_all())
