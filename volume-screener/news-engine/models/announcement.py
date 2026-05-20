"""
Announcement model for corporate filings and news.
Uses Pydantic for validation and SQLAlchemy-compatible structure.
"""

from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field
from .enums import SourceType, PriorityLevel, AnnouncementCategory
import hashlib


@dataclass
class AnnouncementCreate:
    """Schema for creating a new announcement (input from scrapers)."""
    source: SourceType
    ticker: str
    company_name: str
    headline: str
    timestamp: datetime
    pdf_link: Optional[str] = None
    category: AnnouncementCategory = AnnouncementCategory.GENERAL
    raw_data: Optional[dict] = None
    
    def generate_hash(self) -> str:
        """Generate unique hash for deduplication."""
        unique_string = f"{self.source}:{self.ticker}:{self.headline}:{self.timestamp.isoformat()}"
        return hashlib.sha256(unique_string.encode()).hexdigest()[:32]


@dataclass
class Announcement:
    """Full announcement model with all fields."""
    id: int
    hash_id: str
    source: SourceType
    ticker: str
    company_name: str
    headline: str
    timestamp: datetime
    pdf_link: Optional[str] = None
    category: AnnouncementCategory = AnnouncementCategory.GENERAL
    priority: PriorityLevel = PriorityLevel.MEDIUM
    sentiment_score: Optional[float] = None  # -1 to 1
    is_processed: bool = False
    is_alerted: bool = False
    raw_data: Optional[dict] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "hash_id": self.hash_id,
            "source": self.source.value,
            "ticker": self.ticker,
            "company_name": self.company_name,
            "headline": self.headline,
            "timestamp": self.timestamp.isoformat(),
            "pdf_link": self.pdf_link,
            "category": self.category.value,
            "priority": self.priority.value,
            "sentiment_score": self.sentiment_score,
            "is_processed": self.is_processed,
            "is_alerted": self.is_alerted,
            "created_at": self.created_at.isoformat(),
        }
