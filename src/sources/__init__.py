"""
Trend sources package.

Contains integrations for various data sources:
- Hacker News
- RSS Feeds
- Reddit
- GitHub Trending
- arXiv
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from datetime import datetime


class TrendSource(ABC):
    """Abstract base class for trend sources"""

    def __init__(self, source_name: str):
        self.source_name = source_name

    @abstractmethod
    def fetch_trends(self, limit: int = 30) -> List[Dict[str, Any]]:
        """
        Fetch trends from the source.

        Returns list of dicts with keys:
        - title: str
        - description: str
        - url: str
        - score: int (engagement metric)
        - published_at: datetime
        - category: str (optional)
        """
        pass

    @abstractmethod
    def is_relevant(self, trend: Dict[str, Any]) -> bool:
        """
        Check if a trend is relevant to AI/tech.

        Args:
            trend: Trend dictionary

        Returns:
            bool: True if relevant
        """
        pass
