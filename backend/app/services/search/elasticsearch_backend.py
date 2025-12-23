"""
Elasticsearch search backend implementation.

Implements the SearchBackend interface using Elasticsearch for full-text search
with ranking, filtering, and pagination support.
"""

import base64
import json
from typing import Any

from elasticsearch import AsyncElasticsearch
from elasticsearch.exceptions import NotFoundError

from app.core.config import get_settings
from app.services.search.backend import SearchBackend, SearchResult, SearchFilters
from app.utils.normalization import normalize_search_text

settings = get_settings()


class ElasticsearchSearchBackend(SearchBackend):
    """Elasticsearch implementation of SearchBackend."""
    
    def __init__(self, client: AsyncElasticsearch | None = None):
        """
        Initialize Elasticsearch backend.
        
        Args:
            client: Optional Elasticsearch client (creates new one if not provided)
        """
        self.client = client or AsyncElasticsearch(
            hosts=[settings.elasticsearch_url],
            request_timeout=30,
        )
        self.index_name = settings.elasticsearch_index_funds
    
    async def initialize_index(self) -> None:
        """Create the funds index with proper mapping if it doesn't exist."""
        try:
            exists = await self.client.indices.exists(index=self.index_name)
            if not exists:
                mapping = {
                "mappings": {
                    "properties": {
                        "fund_id": {"type": "keyword"},
                        "fund_name": {
                            "type": "text",
                            "analyzer": "standard",
                            "fields": {
                                "keyword": {"type": "keyword"}  # For exact matching and sorting
                            }
                        },
                        "fund_name_norm": {"type": "keyword"},  # Exact match
                        "fund_abbr": {
                            "type": "text",
                            "analyzer": "standard",
                            "fields": {
                                "keyword": {"type": "keyword"}  # For exact matching
                            }
                        },
                        "fund_abbr_norm": {"type": "keyword"},  # Exact match
                        "amc_id": {"type": "keyword"},
                        "amc_name": {"type": "text"},
                        "category": {"type": "keyword"},
                        "risk_level": {"type": "keyword"},
                        "expense_ratio": {"type": "float"},
                        "fund_status": {"type": "keyword"},
                        "fee_band": {"type": "keyword"},  # Derived: low, medium, high
                    }
                },
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,  # Single node setup
                }
            }
                await self.client.indices.create(index=self.index_name, body=mapping)
        except Exception as e:
            # Log but don't fail - index might already exist or there might be a connection issue
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Index initialization note: {e}")
    
    async def search(
        self,
        query: str | None,
        filters: SearchFilters | None,
        sort: str,
        limit: int,
        cursor: str | None = None,
    ) -> SearchResult:
        """
        Search for funds using Elasticsearch.
        
        Implements multi-tier ranking:
        1. Exact match on normalized abbreviation
        2. Exact match on normalized name
        3. Prefix match on normalized abbreviation
        4. Prefix match on normalized name
        5. Substring match on normalized abbreviation
        6. Substring match on normalized name
        7. Fallback to raw fields if normalized missing
        """
        # Build query
        es_query = self._build_query(query, filters)
        
        # Build sort
        es_sort = self._build_sort(sort)
        
        # Handle pagination
        from_size = self._decode_cursor(cursor) if cursor else None
        search_params = {
            "index": self.index_name,
            "body": {
                "query": es_query,
                "sort": es_sort,
                "size": limit + 1,  # Fetch one extra to check for next page
            }
        }
        
        if from_size:
            search_params["body"]["from"] = from_size["from"]
        
        try:
            response = await self.client.search(**search_params)
        except Exception as e:
            # Check for index_not_found_exception or BadRequestError (which may wrap it)
            from elasticsearch.exceptions import NotFoundError, RequestError
            error_str = str(e).lower()
            
            if (isinstance(e, (NotFoundError, RequestError)) or 
                "index_not_found" in error_str or 
                "bad_request" in error_str or
                "400" in error_str):
                # Index doesn't exist yet or query is invalid - return empty results
                return SearchResult(
                    items=[],
                    total=0,
                    next_cursor=None,
                )
            
            # Log other unexpected errors
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Elasticsearch search error: {e}, type: {type(e)}")
            
            # For other errors, return empty results to avoid breaking the API
            return SearchResult(
                items=[],
                total=0,
                next_cursor=None,
            )
        
        # Process results
        hits = response["hits"]["hits"]
        total = response["hits"]["total"]["value"]
        
        has_more = len(hits) > limit
        if has_more:
            hits = hits[:limit]
        
        items = [hit["_source"] for hit in hits]
        
        # Build next cursor
        next_cursor = None
        if has_more and hits:
            next_cursor = self._encode_cursor(
                from_size["from"] + limit if from_size else limit
            )
        
        return SearchResult(
            items=items,
            total=total,
            next_cursor=next_cursor,
        )
    
    def _build_query(
        self, 
        query: str | None, 
        filters: SearchFilters | None
    ) -> dict[str, Any]:
        """Build Elasticsearch query with ranking."""
        must_clauses = []
        should_clauses = []
        
        # Search query with ranking
        if query:
            q_norm = normalize_search_text(query)
            
            # Multi-tier ranking using should clauses (higher score = better match)
            should_clauses.extend([
                # Tier 1: Exact match on normalized abbreviation (highest priority)
                {
                    "term": {
                        "fund_abbr_norm": {
                            "value": q_norm,
                            "boost": 10.0
                        }
                    }
                },
                # Tier 2: Exact match on normalized name
                {
                    "term": {
                        "fund_name_norm": {
                            "value": q_norm,
                            "boost": 9.0
                        }
                    }
                },
                # Tier 3: Prefix match on normalized abbreviation
                {
                    "prefix": {
                        "fund_abbr_norm": {
                            "value": q_norm,
                            "boost": 7.0
                        }
                    }
                },
                # Tier 4: Prefix match on normalized name
                {
                    "prefix": {
                        "fund_name_norm": {
                            "value": q_norm,
                            "boost": 6.0
                        }
                    }
                },
                # Tier 5: Substring match on normalized abbreviation
                {
                    "wildcard": {
                        "fund_abbr_norm": {
                            "value": f"*{q_norm}*",
                            "boost": 5.0
                        }
                    }
                },
                # Tier 6: Substring match on normalized name
                {
                    "wildcard": {
                        "fund_name_norm": {
                            "value": f"*{q_norm}*",
                            "boost": 4.0
                        }
                    }
                },
                # Tier 7: Fallback to raw fields (if normalized missing)
                {
                    "multi_match": {
                        "query": query,  # Use original query for raw fields
                        "fields": ["fund_abbr^2", "fund_name"],
                        "type": "phrase_prefix",
                        "boost": 1.0
                    }
                }
            ])
        
        # Filters
        if filters:
            filter_clauses = []
            
            if filters.get("amc"):
                filter_clauses.append({
                    "terms": {"amc_id": filters["amc"]}
                })
            
            if filters.get("category"):
                filter_clauses.append({
                    "terms": {"category": filters["category"]}
                })
            
            if filters.get("risk"):
                filter_clauses.append({
                    "terms": {"risk_level": filters["risk"]}
                })
            
            # Fee Band (Derived) - handle in query since it's calculated from expense_ratio
            if filters.get("fee_band"):
                fee_band_conditions = []
                for band in filters["fee_band"]:
                    if band == "low":
                        fee_band_conditions.append({
                            "range": {
                                "expense_ratio": {
                                    "lte": 1.0
                                }
                            }
                        })
                    elif band == "medium":
                        fee_band_conditions.append({
                            "range": {
                                "expense_ratio": {
                                    "gt": 1.0,
                                    "lte": 2.0
                                }
                            }
                        })
                    elif band == "high":
                        fee_band_conditions.append({
                            "range": {
                                "expense_ratio": {
                                    "gt": 2.0
                                }
                            }
                        })
                
                if fee_band_conditions:
                    filter_clauses.append({
                        "bool": {
                            "should": fee_band_conditions,
                            "minimum_should_match": 1
                        }
                    })
            
            if filter_clauses:
                must_clauses.append({"bool": {"must": filter_clauses}})
        
        # Status filter (always active funds)
        must_clauses.append({"term": {"fund_status": "RG"}})
        
        # Build final query
        query_dict: dict[str, Any] = {
            "bool": {
                "must": must_clauses,
            }
        }
        
        if should_clauses:
            query_dict["bool"]["should"] = should_clauses
            # Only require should match if there's a search query
            query_dict["bool"]["minimum_should_match"] = 1 if query else 0
        elif not query:
            # If no query, use match_all to return all documents
            query_dict = {"match_all": {}}
            # Still apply filters
            if must_clauses:
                query_dict = {
                    "bool": {
                        "must": must_clauses
                    }
                }
        
        return query_dict
    
    def _build_sort(self, sort: str) -> list[dict[str, Any]]:
        """Build Elasticsearch sort clause."""
        sort_mapping = {
            "name_asc": [{"fund_name.keyword": {"order": "asc"}}, "_score"],
            "name_desc": [{"fund_name.keyword": {"order": "desc"}}, "_score"],
            "fee_asc": [{"expense_ratio": {"order": "asc", "missing": "_last"}}, "_score"],
            "fee_desc": [{"expense_ratio": {"order": "desc", "missing": "_last"}}, "_score"],
            "risk_asc": [{"risk_level": {"order": "asc", "missing": "_last"}}, "_score"],
            "risk_desc": [{"risk_level": {"order": "desc", "missing": "_last"}}, "_score"],
        }
        
        return sort_mapping.get(sort, sort_mapping["name_asc"])
    
    async def index_fund(self, fund_data: dict) -> None:
        """Index a single fund document."""
        await self.client.index(
            index=self.index_name,
            id=fund_data["fund_id"],
            document=fund_data,
        )
    
    async def bulk_index_funds(self, funds_data: list[dict]) -> None:
        """Bulk index multiple fund documents."""
        if not funds_data:
            return
        
        actions = []
        for fund in funds_data:
            actions.append({
                "_index": self.index_name,
                "_id": fund["fund_id"],
                "_source": fund,
            })
        
        from elasticsearch.helpers import async_bulk
        await async_bulk(self.client, actions)
    
    async def delete_fund(self, fund_id: str) -> None:
        """Delete a fund from the index."""
        try:
            await self.client.delete(index=self.index_name, id=fund_id)
        except NotFoundError:
            pass  # Already deleted or never existed
    
    def _encode_cursor(self, from_value: int) -> str:
        """Encode pagination cursor."""
        data = {"from": from_value}
        json_str = json.dumps(data)
        return base64.urlsafe_b64encode(json_str.encode()).decode()
    
    def _decode_cursor(self, cursor: str) -> dict[str, int] | None:
        """Decode pagination cursor."""
        try:
            json_str = base64.urlsafe_b64decode(cursor.encode()).decode()
            return json.loads(json_str)
        except Exception:
            return None
    
    async def get_category_aggregation(self) -> list[dict]:
        """
        Get distinct categories with counts using Elasticsearch aggregation.
        
        Returns:
            List of {value: str, count: int} sorted by count desc, then value asc
        """
        import logging
        logger = logging.getLogger(__name__)
        
        query = {
            "size": 0,  # No documents, only aggregations
            "query": {
                "bool": {
                    "must": [
                        {"term": {"fund_status": "RG"}},
                        {"exists": {"field": "category"}}  # Exclude nulls
                    ]
                }
            },
            "aggs": {
                "categories": {
                    "terms": {
                        "field": "category",
                        "size": 1000,  # Max distinct categories expected
                        "order": [
                            {"_count": "desc"},  # Primary: count descending
                            {"_key": "asc"}      # Secondary: alphabetical
                        ]
                    }
                }
            }
        }
        
        try:
            response = await self.client.search(
                index=self.index_name,
                body=query
            )
            
            buckets = response["aggregations"]["categories"]["buckets"]
            return [
                {"value": bucket["key"], "count": bucket["doc_count"]}
                for bucket in buckets
            ]
        except Exception as e:
            logger.error(f"Elasticsearch category aggregation failed: {e}")
            raise  # Let caller handle fallback
    
    async def get_risk_aggregation(self) -> list[dict]:
        """
        Get distinct risk levels with counts using Elasticsearch aggregation.
        
        Returns:
            List of {value: str, count: int} sorted by risk_level asc (numeric if possible)
        """
        import logging
        logger = logging.getLogger(__name__)
        
        query = {
            "size": 0,
            "query": {
                "bool": {
                    "must": [
                        {"term": {"fund_status": "RG"}},
                        {"exists": {"field": "risk_level"}}
                    ]
                }
            },
            "aggs": {
                "risks": {
                    "terms": {
                        "field": "risk_level",
                        "size": 20,  # Max 8 risk levels, but allow buffer
                        "order": {"_key": "asc"}  # Will sort as string, we'll handle numeric sort in Python
                    }
                }
            }
        }
        
        try:
            response = await self.client.search(
                index=self.index_name,
                body=query
            )
            
            buckets = response["aggregations"]["risks"]["buckets"]
            results = [
                {"value": bucket["key"], "count": bucket["doc_count"]}
                for bucket in buckets
            ]
            
            # Attempt numeric sort for risk levels (fallback to string if not numeric)
            def sort_key(item):
                try:
                    return int(item["value"])
                except (ValueError, TypeError):
                    return item["value"]
            
            results.sort(key=sort_key)
            return results
        except Exception as e:
            logger.error(f"Elasticsearch risk aggregation failed: {e}")
            raise
    
    async def get_amc_aggregation(
        self,
        search_term: str | None = None,
        limit: int = 20,
        cursor: dict | None = None
    ) -> dict:
        """
        Get AMCs with fund counts, supporting search and pagination.
        
        Uses Elasticsearch aggregation with sub-aggregation for AMC name search.
        
        Args:
            search_term: Optional search term to filter AMC names
            limit: Maximum number of results
            cursor: Pagination cursor dict from previous request (contains last_amc_id and last_count)
        
        Returns:
            {
                "items": [{"id": str, "name": str, "count": int}],
                "next_cursor": dict | None
            }
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Build base query
        must_clauses = [{"term": {"fund_status": "RG"}}]
        
        # Add AMC name search if provided
        if search_term:
            must_clauses.append({
                "multi_match": {
                    "query": search_term,
                    "fields": ["amc_name"],
                    "type": "phrase_prefix"  # Prefix matching for typeahead
                }
            })
        
        # Build aggregation with top_hits to get AMC name
        aggs_config = {
            "terms": {
                "field": "amc_id",
                "size": limit + 1,  # Fetch one extra for pagination check
                "order": {"_count": "desc"}
            },
            "aggs": {
                "amc_name": {
                    "top_hits": {
                        "size": 1,
                        "_source": ["amc_name"]
                    }
                }
            }
        }
        
        # Apply cursor-based pagination if provided
        # Note: ES terms aggregation doesn't support cursor directly, so we use a workaround
        # by filtering out results before the cursor position
        if cursor:
            last_amc_id = cursor.get("last_amc_id")
            last_count = cursor.get("last_count")
            if last_amc_id:
                # Add filter to exclude AMCs before cursor
                # This is approximate - for exact pagination, composite aggregation would be better
                # but terms aggregation is simpler and sufficient for most cases
                pass  # We'll handle cursor in post-processing
        
        query = {
            "size": 0,
            "query": {
                "bool": {
                    "must": must_clauses
                }
            },
            "aggs": {
                "amcs": aggs_config
            }
        }
        
        try:
            response = await self.client.search(
                index=self.index_name,
                body=query
            )
            
            buckets = response["aggregations"]["amcs"]["buckets"]
            
            # Apply cursor filtering if needed
            if cursor:
                last_amc_id = cursor.get("last_amc_id")
                last_count = cursor.get("last_count")
                if last_amc_id:
                    # Filter out items before cursor
                    filtered_buckets = []
                    found_cursor = False
                    for bucket in buckets:
                        if found_cursor:
                            filtered_buckets.append(bucket)
                        elif bucket["key"] == last_amc_id:
                            found_cursor = True
                            # Skip the cursor item itself
                    buckets = filtered_buckets
            
            has_more = len(buckets) > limit
            if has_more:
                buckets = buckets[:limit]
            
            items = []
            for bucket in buckets:
                # Extract AMC name from top_hits
                amc_name = "Unknown"
                if bucket.get("amc_name", {}).get("hits", {}).get("hits"):
                    hit = bucket["amc_name"]["hits"]["hits"][0]
                    amc_name = hit["_source"].get("amc_name", "Unknown")
                
                items.append({
                    "id": bucket["key"],
                    "name": amc_name,
                    "count": bucket["doc_count"]
                })
            
            # Build cursor for next page
            next_cursor = None
            if has_more and buckets:
                next_cursor = {
                    "last_amc_id": buckets[-1]["key"],
                    "last_count": buckets[-1]["doc_count"]
                }
            
            return {
                "items": items,
                "next_cursor": next_cursor
            }
        except Exception as e:
            logger.error(f"Elasticsearch AMC aggregation failed: {e}")
            raise
    
    async def close(self) -> None:
        """Close the Elasticsearch client."""
        await self.client.close()

