import sys
import os

# Ensure we can import from news-engine
sys.path.append(os.getcwd())

from worker import fetch_market_updates, analyze_news_item

def main():
    print("🚀 Forcing manual news fetch from BSE...")
    
    # Run the task synchronously for immediate feedback
    # In production, we usually use .delay() but here we want to see output
    try:
        result = fetch_market_updates(source="BSE", days_back=1)
        print("\n✅ Fetch Complete!")
        print(f"📊 Summary: {result}")
        print("\nRefresh your frontend to see the new items!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
