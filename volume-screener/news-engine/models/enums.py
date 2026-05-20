"""Enumerations for News Intelligence Engine."""

from enum import Enum


class SourceType(str, Enum):
    """Source of the announcement/news."""
    BSE = "bse"
    NSE = "nse"
    TWITTER = "twitter"
    NEWS_RSS = "news_rss"
    SEBI = "sebi"


class PriorityLevel(str, Enum):
    """Priority/impact level of the announcement."""
    CRITICAL = "critical"    # Board meetings, results, major acquisitions
    HIGH = "high"            # Insider trading, regulatory actions
    MEDIUM = "medium"        # AGM notices, dividend announcements
    LOW = "low"              # Routine filings, compliance updates
    NOISE = "noise"          # Irrelevant/duplicate


class AnnouncementCategory(str, Enum):
    """Category of corporate announcement."""
    BOARD_MEETING = "board_meeting"
    FINANCIAL_RESULTS = "financial_results"
    DIVIDEND = "dividend"
    BONUS = "bonus"
    STOCK_SPLIT = "stock_split"
    ACQUISITION = "acquisition"
    INSIDER_TRADING = "insider_trading"
    REGULATORY = "regulatory"
    AGM_EGM = "agm_egm"
    RIGHTS_ISSUE = "rights_issue"
    BUYBACK = "buyback"
    DELISTING = "delisting"
    GENERAL = "general"
    OTHER = "other"
