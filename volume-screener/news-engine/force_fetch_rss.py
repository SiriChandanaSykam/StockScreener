"""
Force Fetch RSS News - Manual trigger for testing
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from worker import fetch_rss_news


def main():
    print("🚀 Forcing manual RSS news fetch...\n")
    
    # Priority sources (Moneycontrol + ET)
    priority_sources = [
        "Moneycontrol",
        "Moneycontrol Markets", 
        "Economic Times Markets",
        "Economic Times Stocks",
    ]
    
    print(f"📡 Fetching from: {priority_sources}\n")
    
    try:
        # Run synchronously (not via .delay())
        result = fetch_rss_news(sources=priority_sources)
        
        print("\n✅ Fetch Complete!")
        print(f"📊 Summary:")
        print(f"   Total received: {result.get('total_received', 0)}")
        print(f"   New inserted: {result.get('new_inserted', 0)}")
        print(f"   Duplicates: {result.get('duplicates_skipped', 0)}")
        print("\n🔄 Refresh your frontend to see the new items!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
