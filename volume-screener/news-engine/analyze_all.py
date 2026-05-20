"""
Analyze all unprocessed news items with Gemini AI.
"""
import os
import sys
import asyncio
from dotenv import load_dotenv

# Add project path
sys.path.insert(0, os.path.dirname(__file__))

from storage.database import async_session_maker, init_db
from storage.models import NewsItem
from services.ai_service import MarketAnalyst
from sqlalchemy import select

async def analyze_all():
    # Load env
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
    
    # Init DB
    await init_db()
    
    # Create analyst (will use Gemini if key exists)
    analyst = MarketAnalyst(mock_mode=False)
    print(f"🤖 Mode: {'MOCK' if analyst.mock_mode else 'GEMINI AI'}")
    
    async with async_session_maker() as session:
        # Get unprocessed items
        query = select(NewsItem).where(NewsItem.is_processed == False)
        result = await session.execute(query)
        items = result.scalars().all()
        
        print(f"📰 Found {len(items)} unprocessed items")
        
        for i, item in enumerate(items, 1):
            print(f"\n[{i}/{len(items)}] Analyzing: {item.headline[:60]}...")
            
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
                
                print(f"   ✅ Score: {analysis.relevance_score}/10 | Sentiment: {analysis.sentiment}")
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        await session.commit()
        print(f"\n🎉 Done! Analyzed {len(items)} items.")

if __name__ == "__main__":
    asyncio.run(analyze_all())
