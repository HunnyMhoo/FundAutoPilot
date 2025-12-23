"""Elasticsearch client initialization and management."""

from elasticsearch import AsyncElasticsearch
from functools import lru_cache

from app.core.config import get_settings

settings = get_settings()


@lru_cache
def get_elasticsearch_client() -> AsyncElasticsearch:
    """
    Get or create Elasticsearch client (singleton).
    
    Returns:
        AsyncElasticsearch client instance
    """
    return AsyncElasticsearch(
        hosts=[settings.elasticsearch_url],
        request_timeout=30,
    )


async def close_elasticsearch_client() -> None:
    """Close Elasticsearch client connection."""
    client = get_elasticsearch_client()
    await client.close()

