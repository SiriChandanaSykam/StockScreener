"""
News Digest Generator

Generates a summary of important news for a given time period.
Can be used for:
- Daily digest emails
- Morning briefings
- WhatsApp/Telegram summaries
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


@dataclass
class DigestItem:
    """Single item in the digest."""
    headline: str
    ticker: str
    sentiment: str
    score: int
    source: str
    link: str


@dataclass
class NewsDigest:
    """Complete news digest."""
    period_start: datetime
    period_end: datetime
    total_items: int
    high_impact_count: int
    bullish_count: int
    bearish_count: int
    top_items: List[DigestItem]
    by_ticker: Dict[str, List[DigestItem]]
    
    def to_markdown(self) -> str:
        """Generate markdown summary."""
        lines = []
        
        lines.append("# 📰 News Digest")
        lines.append(f"**Period:** {self.period_start.strftime('%d %b %Y %H:%M')} - {self.period_end.strftime('%d %b %Y %H:%M')}")
        lines.append("")
        
        # Summary stats
        lines.append("## 📊 Summary")
        lines.append(f"- Total News: **{self.total_items}**")
        lines.append(f"- High Impact (8+): **{self.high_impact_count}**")
        lines.append(f"- 🟢 Bullish: **{self.bullish_count}**")
        lines.append(f"- 🔴 Bearish: **{self.bearish_count}**")
        lines.append("")
        
        # Top items
        if self.top_items:
            lines.append("## 🔥 Top Stories")
            for i, item in enumerate(self.top_items[:10], 1):
                emoji = "🟢" if item.sentiment == "Bullish" else "🔴" if item.sentiment == "Bearish" else "⚪"
                lines.append(f"{i}. {emoji} **[{item.score}/10]** {item.headline[:80]}")
                if item.ticker != "MARKET":
                    lines.append(f"   📌 {item.ticker} | {item.source}")
                lines.append("")
        
        # By ticker (top 5 tickers with most news)
        if self.by_ticker:
            lines.append("## 📈 News by Stock")
            sorted_tickers = sorted(
                self.by_ticker.items(),
                key=lambda x: len(x[1]),
                reverse=True
            )[:5]
            
            for ticker, items in sorted_tickers:
                if ticker == "MARKET":
                    continue
                lines.append(f"### {ticker} ({len(items)} news)")
                for item in items[:3]:
                    emoji = "🟢" if item.sentiment == "Bullish" else "🔴" if item.sentiment == "Bearish" else "⚪"
                    lines.append(f"  - {emoji} {item.headline[:60]}...")
                lines.append("")
        
        return "\n".join(lines)
    
    def to_text(self) -> str:
        """Generate plain text summary (for WhatsApp/Telegram)."""
        lines = []
        
        lines.append("📰 *NEWS DIGEST*")
        lines.append(f"📅 {self.period_start.strftime('%d %b')} - {self.period_end.strftime('%d %b %H:%M')}")
        lines.append("")
        lines.append(f"📊 Total: {self.total_items} | 🔥 High Impact: {self.high_impact_count}")
        lines.append(f"🟢 Bullish: {self.bullish_count} | 🔴 Bearish: {self.bearish_count}")
        lines.append("")
        
        if self.top_items:
            lines.append("*TOP STORIES:*")
            for i, item in enumerate(self.top_items[:5], 1):
                emoji = "🟢" if item.sentiment == "Bullish" else "🔴" if item.sentiment == "Bearish" else "⚪"
                lines.append(f"{i}. {emoji} [{item.score}/10] {item.headline[:60]}...")
        
        return "\n".join(lines)


async def generate_digest(
    hours: int = 24,
    min_score: int = 5,
) -> NewsDigest:
    """
    Generate news digest for the last N hours.
    
    Args:
        hours: Look back period in hours
        min_score: Minimum impact score to include
        
    Returns:
        NewsDigest object with summary and top items
    """
    from storage.database import async_session_maker, init_db
    from storage.models import NewsItem
    from sqlalchemy import select, desc
    
    await init_db()
    
    period_end = datetime.utcnow()
    period_start = period_end - timedelta(hours=hours)
    
    async with async_session_maker() as session:
        # Get all items in period
        query = (
            select(NewsItem)
            .where(NewsItem.published_at >= period_start)
            .order_by(desc(NewsItem.impact_score), desc(NewsItem.published_at))
        )
        
        result = await session.execute(query)
        items = result.scalars().all()
        
        # Process items
        digest_items = []
        by_ticker: Dict[str, List[DigestItem]] = {}
        
        bullish_count = 0
        bearish_count = 0
        high_impact_count = 0
        
        for item in items:
            # Determine sentiment from ai_analysis
            sentiment = "Neutral"
            if item.ai_analysis:
                sentiment = item.ai_analysis.get("sentiment", "Neutral")
            elif item.sentiment_score:
                if item.sentiment_score > 0.3:
                    sentiment = "Bullish"
                elif item.sentiment_score < -0.3:
                    sentiment = "Bearish"
            
            score = int(item.impact_score or 5)
            
            if sentiment == "Bullish":
                bullish_count += 1
            elif sentiment == "Bearish":
                bearish_count += 1
            
            if score >= 8:
                high_impact_count += 1
            
            if score >= min_score:
                digest_item = DigestItem(
                    headline=item.headline,
                    ticker=item.ticker or "MARKET",
                    sentiment=sentiment,
                    score=score,
                    source=item.source_name,
                    link=item.source_url or "",
                )
                digest_items.append(digest_item)
                
                # Group by ticker
                ticker = item.ticker or "MARKET"
                if ticker not in by_ticker:
                    by_ticker[ticker] = []
                by_ticker[ticker].append(digest_item)
        
        return NewsDigest(
            period_start=period_start,
            period_end=period_end,
            total_items=len(items),
            high_impact_count=high_impact_count,
            bullish_count=bullish_count,
            bearish_count=bearish_count,
            top_items=digest_items[:20],
            by_ticker=by_ticker,
        )


async def main():
    print("=" * 60)
    print("📰 Generating News Digest")
    print("=" * 60)
    
    digest = await generate_digest(hours=24, min_score=5)
    
    # Print markdown version
    print("\n" + digest.to_markdown())
    
    # Save to file
    output_path = os.path.join(os.path.dirname(__file__), "digest.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(digest.to_markdown())
    
    print(f"\n✅ Digest saved to: {output_path}")
    
    # Also print WhatsApp format
    print("\n" + "=" * 60)
    print("📱 WhatsApp/Telegram Format:")
    print("=" * 60)
    print(digest.to_text())


if __name__ == "__main__":
    asyncio.run(main())
