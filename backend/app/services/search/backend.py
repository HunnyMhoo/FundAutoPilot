"""
Abstract base class for search backends.

This abstraction allows switching between different search implementations
(e.g., SQL, Elasticsearch) without changing the service layer.
"""

from abc import ABC, abstractmethod
from typing import TypedDict


class SearchResult(TypedDict):
    """Search result structure."""
    items: list[dict]
    total: int
    next_cursor: str | None


class SearchFilters(TypedDict, total=False):
    """Search filter structure."""
    amc: list[str]
    category: list[str]
    risk: list[str]
    fee_band: list[str]


class SearchBackend(ABC):
    """Abstract base class for search backends."""
    
    @abstractmethod
    async def search(
        self,
        query: str | None,
        filters: SearchFilters | None,
        sort: str,
        limit: int,
        cursor: str | None = None,
    ) -> SearchResult:
        """
        Search for funds.
        
        Args:
            query: Search query string (normalized)
            filters: Filter dictionary (amc, category, risk, fee_band)
            sort: Sort order ('name_asc', 'name_desc', 'fee_asc', etc.)
            limit: Maximum number of results
            cursor: Pagination cursor
            
        Returns:
            SearchResult with items, total count, and next cursor
        """
        pass
    
    @abstractmethod
    async def index_fund(self, fund_data: dict) -> None:
        """
        Index a single fund document.
        
        Args:
            fund_data: Fund document to index
        """
        pass
    
    @abstractmethod
    async def bulk_index_funds(self, funds_data: list[dict]) -> None:
        """
        Bulk index multiple fund documents.
        
        Args:
            funds_data: List of fund documents to index
        """
        pass
    
    @abstractmethod
    async def delete_fund(self, fund_id: str) -> None:
        """
        Delete a fund from the index.
        
        Args:
            fund_id: Fund ID to delete
        """
        pass
    
    @abstractmethod
    async def initialize_index(self) -> None:
        """Initialize/create the search index if it doesn't exist."""
        pass

