"""Ingestors package - Data feeders/scrapers for various sources."""

# Lazy imports to avoid circular dependency issues
# Import specific scrapers when needed, not at package level

__all__ = [
    "BSEScraper",
    "RSSNewsScraper",
]


def __getattr__(name):
    """Lazy import to avoid import errors at module load time."""
    if name == "BSEScraper":
        try:
            from .bse_scraper import BSEScraper
            return BSEScraper
        except ImportError:
            raise ImportError("BSEScraper requires additional dependencies")
    elif name == "RSSNewsScraper":
        from .rss_scraper import RSSNewsScraper
        return RSSNewsScraper
    elif name == "BaseIngestor":
        try:
            from .base import BaseIngestor
            return BaseIngestor
        except ImportError:
            raise ImportError("BaseIngestor not found")
    raise AttributeError(f"module 'ingestors' has no attribute '{name}'")
