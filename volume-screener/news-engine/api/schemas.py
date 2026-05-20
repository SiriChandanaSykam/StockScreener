"""
Pydantic Schemas for News Intelligence Engine API.

Provides request/response models with proper validation
and flattened AI analysis fields for frontend consumption.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class SentimentEnum(str, Enum):
    """Allowed sentiment values."""
    BULLISH = "Bullish"
    BEARISH = "Bearish"
    NEUTRAL = "Neutral"


class PriorityEnum(str, Enum):
    """Priority levels for news items."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NOISE = "noise"


# =============================================================================
# Response Schemas
# =============================================================================

class AIAnalysisResponse(BaseModel):
    """Flattened AI analysis data."""
    relevance_score: int = Field(default=0, ge=0, le=10, description="Impact score 1-10")
    sentiment: str = Field(default="Neutral", description="Bullish/Bearish/Neutral")
    summary: str = Field(default="", description="Max 15 word summary")
    category: Optional[str] = Field(default=None, description="News category")
    confidence: float = Field(default=0.0, ge=0, le=1, description="Model confidence")
    key_metrics: Optional[Dict[str, Any]] = Field(default=None, description="Extracted numbers")
    reasoning: Optional[str] = Field(default=None, description="Analysis reasoning")


class NewsItemResponse(BaseModel):
    """
    Complete news item response with flattened AI analysis.
    
    AI analysis fields are promoted to top level for easy frontend access.
    """
    model_config = ConfigDict(from_attributes=True)
    
    # Core fields
    id: str = Field(..., description="UUID of the news item")
    ticker: str = Field(..., description="Stock ticker/code")
    company_name: Optional[str] = Field(default=None, description="Company name")
    headline: str = Field(..., description="News headline")
    
    # Source info
    source_url: Optional[str] = Field(default=None, description="Link to PDF/original")
    source_name: str = Field(default="BSE", description="BSE, NSE, etc.")
    
    # Timestamps
    published_at: datetime = Field(..., description="When the news was published")
    created_at: datetime = Field(..., description="When we ingested it")
    
    # Classification (from rule-based)
    category: Optional[str] = Field(default=None, description="financial_results, etc.")
    
    # === FLATTENED AI ANALYSIS ===
    # These are promoted from ai_analysis JSON for easy frontend access
    relevance_score: Optional[float] = Field(default=None, description="AI relevance 1-10")
    sentiment: Optional[str] = Field(default=None, description="Bullish/Bearish/Neutral")
    sentiment_score: Optional[float] = Field(default=None, description="Numeric sentiment -1 to 1")
    priority: Optional[str] = Field(default=None, description="critical/high/medium/low/noise")
    ai_summary: Optional[str] = Field(default=None, description="AI-generated summary")
    
    # Processing status
    is_processed: bool = Field(default=False, description="Has AI analyzed this?")
    is_alerted: bool = Field(default=False, description="Has alert been sent?")
    
    # Full AI analysis (for detailed view)
    ai_analysis: Optional[Dict[str, Any]] = Field(default=None, description="Full AI analysis JSON")
    
    @classmethod
    def from_db_model(cls, db_item) -> "NewsItemResponse":
        """
        Create response from database model with flattened AI analysis.
        """
        # Extract AI analysis fields
        ai = db_item.ai_analysis or {}
        
        return cls(
            id=str(db_item.id),
            ticker=db_item.ticker,
            company_name=db_item.company_name,
            headline=db_item.headline,
            source_url=db_item.source_url,
            source_name=db_item.source_name,
            published_at=db_item.published_at,
            created_at=db_item.created_at,
            category=db_item.category or ai.get("category"),
            relevance_score=db_item.impact_score or ai.get("relevance_score"),
            sentiment=ai.get("sentiment"),
            sentiment_score=db_item.sentiment_score,
            priority=db_item.priority or _score_to_priority(ai.get("relevance_score", 0)),
            ai_summary=ai.get("summary"),
            is_processed=db_item.is_processed,
            is_alerted=db_item.is_alerted,
            ai_analysis=db_item.ai_analysis,
        )


class NewsFeedResponse(BaseModel):
    """Paginated news feed response."""
    items: List[NewsItemResponse] = Field(default_factory=list)
    total: int = Field(default=0, description="Total matching items")
    limit: int = Field(default=50)
    offset: int = Field(default=0)
    has_more: bool = Field(default=False, description="Are there more items?")


class NewsLatestResponse(BaseModel):
    """Response for polling endpoint."""
    items: List[NewsItemResponse] = Field(default_factory=list)
    count: int = Field(default=0, description="Number of new items")
    latest_id: Optional[str] = Field(default=None, description="ID of newest item")
    latest_timestamp: Optional[datetime] = Field(default=None, description="Timestamp of newest")


# =============================================================================
# Request Schemas
# =============================================================================

class NewsFeedQuery(BaseModel):
    """Query parameters for news feed endpoint."""
    min_relevance: int = Field(default=0, ge=0, le=10, description="Minimum relevance score")
    ticker: Optional[str] = Field(default=None, description="Filter by ticker")
    sentiment: Optional[SentimentEnum] = Field(default=None, description="Filter by sentiment")
    category: Optional[str] = Field(default=None, description="Filter by category")
    priority: Optional[PriorityEnum] = Field(default=None, description="Filter by priority")
    source: Optional[str] = Field(default=None, description="Filter by source (BSE, NSE)")
    limit: int = Field(default=50, ge=1, le=200, description="Items per page")
    offset: int = Field(default=0, ge=0, description="Pagination offset")
    processed_only: bool = Field(default=False, description="Only AI-processed items")


class NewsLatestQuery(BaseModel):
    """Query parameters for latest/polling endpoint."""
    since_id: Optional[str] = Field(default=None, description="Return items after this ID")
    since_timestamp: Optional[datetime] = Field(default=None, description="Return items after this time")
    min_relevance: int = Field(default=0, ge=0, le=10, description="Minimum relevance score")
    ticker: Optional[str] = Field(default=None, description="Filter by ticker")
    limit: int = Field(default=20, ge=1, le=100, description="Max items to return")


# =============================================================================
# Health & Stats Schemas
# =============================================================================

class HealthResponse(BaseModel):
    """API health check response."""
    status: str = "healthy"
    version: str = "1.0.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class StatsResponse(BaseModel):
    """API statistics response."""
    total_items: int = 0
    processed_items: int = 0
    unprocessed_items: int = 0
    items_today: int = 0
    items_by_source: Dict[str, int] = Field(default_factory=dict)
    items_by_sentiment: Dict[str, int] = Field(default_factory=dict)


# =============================================================================
# Helpers
# =============================================================================

def _score_to_priority(relevance_score: int) -> str:
    """Convert relevance score to priority level."""
    if not relevance_score:
        return "medium"
    if relevance_score >= 9:
        return "critical"
    elif relevance_score >= 7:
        return "high"
    elif relevance_score >= 5:
        return "medium"
    elif relevance_score >= 3:
        return "low"
    else:
        return "noise"
