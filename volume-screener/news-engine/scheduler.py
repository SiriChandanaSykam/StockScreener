"""
News Intelligence Scheduler

Automatically fetches news from all sources and runs FinBERT analysis.
Uses APScheduler for background job scheduling.

Run: python scheduler.py
"""

import asyncio
import logging
import signal
import sys
import os
from datetime import datetime

# Add paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("scheduler.log"),
    ]
)
logger = logging.getLogger("NewsScheduler")


class NewsScheduler:
    """
    Background scheduler for automatic news fetching and analysis.
    
    Default: Fetches every 2 minutes.
    """
    
    def __init__(
        self,
        fetch_interval_minutes: int = 2,
        include_et: bool = True,
        include_mc: bool = True,
        include_sebi: bool = True,
    ):
        self.fetch_interval = fetch_interval_minutes
        self.include_et = include_et
        self.include_mc = include_mc
        self.include_sebi = include_sebi
        
        self.running = False
        self.cycle_count = 0
        
    async def run_fetch_cycle(self):
        """
        Single fetch and analyze cycle.
        """
        self.cycle_count += 1
        
        logger.info("=" * 60)
        logger.info(f"📰 CYCLE #{self.cycle_count} - {datetime.now().strftime('%H:%M:%S')}")
        logger.info("=" * 60)
        
        try:
            from fetch_all_sources import fetch_all_sources, store_and_analyze
            
            # Fetch from all sources
            items = await fetch_all_sources(
                include_et=self.include_et,
                include_mc=self.include_mc,
                include_sebi=self.include_sebi,
                max_per_source=20
            )
            
            # Store and analyze with FinBERT
            await store_and_analyze(items, run_analysis=True)
            
            logger.info(f"✅ Cycle #{self.cycle_count} completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Cycle #{self.cycle_count} failed: {e}", exc_info=True)
    
    async def start(self):
        """
        Start the scheduler loop.
        """
        self.running = True
        
        logger.info("🚀 News Scheduler Starting...")
        logger.info(f"   Fetch interval: Every {self.fetch_interval} minutes")
        logger.info(f"   Sources: ET={self.include_et}, MC={self.include_mc}, SEBI={self.include_sebi}")
        logger.info("   Press Ctrl+C to stop\n")
        
        # Run initial cycle immediately
        await self.run_fetch_cycle()
        
        # Schedule loop
        while self.running:
            # Wait for next interval
            logger.info(f"⏳ Next fetch in {self.fetch_interval} minutes...")
            
            try:
                await asyncio.sleep(self.fetch_interval * 60)
                
                if self.running:
                    await self.run_fetch_cycle()
                    
            except asyncio.CancelledError:
                break
        
        logger.info("👋 Scheduler stopped")
    
    def stop(self):
        """
        Stop the scheduler gracefully.
        """
        logger.info("🛑 Stopping scheduler...")
        self.running = False


def main():
    """
    Main entry point.
    """
    print("=" * 60)
    print("📰 News Intelligence Scheduler")
    print("   Real-time news monitoring with FinBERT AI")
    print("=" * 60)
    print()
    
    # Get config from environment
    interval = int(os.getenv("FETCH_INTERVAL_MINUTES", "2"))
    
    scheduler = NewsScheduler(
        fetch_interval_minutes=interval,
        include_et=True,
        include_mc=True,
        include_sebi=True,
    )
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        scheduler.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Run
    try:
        asyncio.run(scheduler.start())
    except KeyboardInterrupt:
        print("\n👋 Scheduler stopped by user")


if __name__ == "__main__":
    main()
