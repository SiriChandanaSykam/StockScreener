"""
Base ingestor abstract class.
All data feeders inherit from this.
"""

from abc import ABC, abstractmethod
from typing import List

# Handle both module and standalone imports
try:
    from ..models import AnnouncementCreate
except ImportError:
    from models import AnnouncementCreate


class BaseIngestor(ABC):
    """Abstract base class for all data ingestors."""
    
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the name of this data source."""
        pass
    
    @abstractmethod
    async def fetch(self, **kwargs) -> List[AnnouncementCreate]:
        """
        Fetch announcements from the source.
        
        Returns:
            List of AnnouncementCreate objects ready for storage.
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the source is accessible.
        
        Returns:
            True if source is healthy, False otherwise.
        """
        pass
