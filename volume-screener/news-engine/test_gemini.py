import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.join(os.getcwd(), 'news-engine'))

from services.ai_service import MarketAnalyst

def test_gemini():
    env_path = os.path.join(os.getcwd(), '.env')
    load_dotenv(env_path)
    
    api_key = os.getenv("GEMINI_API_KEY")
    print(f"🔑 Checking for Gemini API Key... {'✅ Found' if api_key else '❌ Not Found'}")
    if api_key:
        print(f"   Key length: {len(api_key)}")
        print("\n⚠️  Please add GEMINI_API_KEY to your .env file to test real analysis.")
        print("   Example: GEMINI_API_KEY=AIzaSy...")
    
    # Initialize analyst (will auto-detect key)
    analyst = MarketAnalyst(mock_mode=False) # Try to force real mode
    
    print(f"\n🤖 Analyst Mode: {'MOCK' if analyst.mock_mode else 'REAL GEMINI'}")
    
    headline = "Tata Motors shares jump 5% on strong JLR sales"
    print(f"\n📰 Analyzing Headline: '{headline}'")
    
    result = analyst.analyze_text(headline, ticker="TATAMOTORS")
    
    print("\n📊 Analysis Result:")
    print(f"   Score: {result.relevance_score}/10")
    print(f"   Sentiment: {result.sentiment}")
    print(f"   Summary: {result.summary}")
    print(f"   Reasoning: {result.reasoning}")

if __name__ == "__main__":
    test_gemini()
