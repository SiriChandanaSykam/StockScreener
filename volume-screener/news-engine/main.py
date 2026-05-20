"""
News Intelligence Engine - FastAPI Application Entry Point.

Run with:
    uvicorn news_engine.main:app --reload --port 8001

Or for production:
    uvicorn news_engine.main:app --host 0.0.0.0 --port 8001 --workers 4
"""

from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Handle both module and standalone imports
try:
    from .api.routes import router as news_router
    from .storage.database import init_db, close_db
except ImportError:
    from api.routes import router as news_router
    from storage.database import init_db, close_db


# =============================================================================
# Application Lifespan (Startup/Shutdown)
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    - Startup: Initialize database
    - Shutdown: Close connections
    """
    # Startup
    print("🚀 Starting News Intelligence Engine...")
    await init_db()
    print("✅ Database initialized")
    
    yield
    
    # Shutdown
    print("🔒 Shutting down News Intelligence Engine...")
    await close_db()
    print("✅ Connections closed")


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="News Intelligence Engine",
    description="""
    ## 📰 High-Frequency News Intelligence for Indian Stock Markets
    
    Real-time ingestion and AI analysis of corporate filings from BSE/NSE.
    
    ### Features
    - **News Feed**: Paginated, filterable news with AI analysis
    - **Live Polling**: Get latest items for real-time alerts
    - **Smart Filtering**: By ticker, sentiment, relevance, priority
    
    ### Quick Start
    ```bash
    # Get high-impact news
    GET /news/feed?min_relevance=7
    
    # Poll for new items
    GET /news/latest?min_relevance=8
    
    # Filter by ticker
    GET /news/feed?ticker=TCS&sentiment=Bullish
    ```
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# =============================================================================
# CORS Middleware
# =============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)


# =============================================================================
# Root Endpoint
# =============================================================================

@app.get("/", tags=["Root"])
async def root():
    """
    API root - basic info and health check.
    """
    return {
        "name": "News Intelligence Engine",
        "version": "1.0.0",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "docs": "/docs",
        "endpoints": {
            "feed": "/news/feed",
            "latest": "/news/latest",
            "stats": "/news/stats/overview",
            "tickers": "/news/tickers/list",
            "health": "/news/health",
        }
    }


# =============================================================================
# Include Routers
# =============================================================================

app.include_router(news_router)


# =============================================================================
# Direct execution for testing
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("News Intelligence Engine - Starting...")
    print("=" * 60)
    print("\n📡 API will be available at: http://localhost:8001")
    print("📖 Docs: http://localhost:8001/docs")
    print("\n")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info",
    )
