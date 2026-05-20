"""
Test FinBERT Integration

Run this to verify FinBERT is working correctly.
"""
import os
import sys

# Add project path
sys.path.insert(0, os.path.dirname(__file__))

from services.ai_service import MarketAnalyst


def test_finbert():
    print("=" * 60)
    print("🧪 Testing FinBERT Integration")
    print("=" * 60)
    
    # Create analyst with FinBERT mode
    analyst = MarketAnalyst(mock_mode=False, ai_mode="finbert")
    
    print(f"\n📊 AI Mode: {analyst.ai_mode}")
    print(f"🤖 FinBERT loaded: {analyst.finbert is not None}")
    
    test_headlines = [
        ("Reliance Industries posts 45% profit growth in Q3", "RELIANCE"),
        ("TCS faces regulatory penalties from SEBI", "TCS"),
        ("Infosys announces $2B acquisition of US tech company", "INFY"),
        ("Markets remain flat amid global uncertainty", "MARKET"),
        ("HDFC Bank declares record dividend of ₹19 per share", "HDFCBANK"),
        ("Adani Group stocks crash 20% on fraud allegations", "ADANIENT"),
        ("Zomato IPO gets oversubscribed by 38 times", "ZOMATO"),
        ("RBI keeps repo rate unchanged at 6.5%", "MARKET"),
    ]
    
    print("\n" + "=" * 60)
    print("📰 Analyzing Sample Headlines...")
    print("=" * 60)
    
    for headline, ticker in test_headlines:
        result = analyst.analyze_text(headline=headline, ticker=ticker)
        
        # Color code
        if result.sentiment == "Bullish":
            emoji = "🟢"
        elif result.sentiment == "Bearish":
            emoji = "🔴"
        else:
            emoji = "⚪"
        
        print(f"\n{emoji} [{result.relevance_score}/10] {result.sentiment}")
        print(f"   {headline}")
        print(f"   → {result.reasoning}")
        print(f"   → Model: {result.model_version}")
    
    print("\n" + "=" * 60)
    print("✅ FinBERT Integration Test Complete!")
    print("=" * 60)
    
    return analyst


if __name__ == "__main__":
    test_finbert()
