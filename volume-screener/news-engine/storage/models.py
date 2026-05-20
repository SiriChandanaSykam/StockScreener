"""
SQLAlchemy Models for News Intelligence Engine.

Uses AsyncSQLAlchemy for FastAPI compatibility.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    Boolean,
    Float,
    JSON,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.types import TypeDecorator, CHAR

# Handle both module and standalone imports
try:
    from .database import Base
except ImportError:
    from database import Base


class GUID(TypeDecorator):
    """
    Platform-independent GUID type.
    Uses PostgreSQL's UUID type when available, otherwise CHAR(32).
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_UUID())
        else:
            return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value).hex
            else:
                return value.hex

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if not isinstance(value, uuid.UUID):
            return uuid.UUID(value)
        return value


class NewsItem(Base):
    """
    Core model for storing news and corporate announcements.
    
    Indexes:
    - ticker: For filtering by stock
    - published_at: For time-based queries
    - source_url: Unique constraint for deduplication
    - headline + published_at: Composite for additional dedup
    """
    __tablename__ = "news_items"
    
    # Primary key - UUID for distributed systems compatibility
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    
    # Core fields
    ticker = Column(String(20), nullable=False, index=True)
    company_name = Column(String(255), nullable=True)
    headline = Column(Text, nullable=False)
    raw_body = Column(Text, nullable=True)  # Full announcement text if available
    
    # Source tracking
    source_url = Column(String(1024), nullable=True, unique=True)  # PDF/attachment URL
    source_name = Column(String(50), nullable=False, default="BSE")  # BSE, NSE, Twitter, etc.
    
    # Timestamps
    published_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Classification (from rule-based categorization)
    category = Column(String(50), nullable=True)  # financial_results, board_meeting, etc.
    
    # AI Analysis (to be populated in Phase 3)
    ai_analysis = Column(JSON, nullable=True, default=None)
    # Expected structure:
    # {
    #     "summary": "...",
    #     "sentiment": 0.75,  # -1 to 1
    #     "impact_score": 8,  # 1-10
    #     "priority": "high",
    #     "key_points": ["...", "..."],
    #     "affected_stocks": ["SYMBOL1", "SYMBOL2"],
    #     "model_version": "gpt-4-turbo",
    #     "processed_at": "2026-01-12T22:00:00Z"
    # }
    
    # Processing status
    is_processed = Column(Boolean, nullable=False, default=False)
    is_alerted = Column(Boolean, nullable=False, default=False)
    
    # Sentiment score (-1 to 1, populated by AI)
    sentiment_score = Column(Float, nullable=True)
    
    # Impact score (1-10, populated by AI)
    impact_score = Column(Float, nullable=True)
    
    # Priority level
    priority = Column(String(20), nullable=True)  # critical, high, medium, low, noise
    
    # Raw data from scraper (for debugging/reprocessing)
    raw_data = Column(JSON, nullable=True)
    
    # Composite unique constraint for deduplication fallback
    # (when source_url is not available)
    __table_args__ = (
        Index('ix_news_headline_published', 'headline', 'published_at'),
        UniqueConstraint('headline', 'published_at', 'ticker', name='uq_news_item_dedup'),
    )
    
    def __repr__(self) -> str:
        return f"<NewsItem(id={self.id}, ticker={self.ticker}, headline={self.headline[:50]}...)>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": str(self.id),
            "ticker": self.ticker,
            "company_name": self.company_name,
            "headline": self.headline,
            "source_url": self.source_url,
            "source_name": self.source_name,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "category": self.category,
            "priority": self.priority,
            "sentiment_score": self.sentiment_score,
            "impact_score": self.impact_score,
            "is_processed": self.is_processed,
            "is_alerted": self.is_alerted,
            "ai_analysis": self.ai_analysis,
        }
