"""Fund service for business logic operations."""

import base64
import json
import logging
import time
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, Any

from sqlalchemy import select, and_, or_, func, case, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.database import SyncSessionLocal
from app.models.fund_orm import Fund, AMC, FundReturnSnapshot
from app.models.fund import FundSummary, FundListResponse, CursorData
from app.models.peer_ranking import PeerRank
from app.services.search.elasticsearch_backend import ElasticsearchSearchBackend
from app.services.peer_ranking_service import PeerRankingService
from app.services.representative_class_service import RepresentativeClassService
from app.core.elasticsearch import get_elasticsearch_client

logger = logging.getLogger(__name__)

settings = get_settings()

# Simple in-memory cache for meta stats (TTL: 5 minutes = 300 seconds)
_meta_cache: Dict[str, tuple[Dict[str, Any], float]] = {}
CACHE_TTL = 300  # 5 minutes


class FundService:
    """Service for fund-related business logic."""
    
    def __init__(self, db: AsyncSession, search_backend: ElasticsearchSearchBackend | None = None):
        self.db = db
        # Initialize search backend if Elasticsearch is enabled
        if settings.elasticsearch_enabled:
            self.search_backend = search_backend or ElasticsearchSearchBackend(get_elasticsearch_client())
        else:
            self.search_backend = None
    
    async def list_funds(
        self,
        limit: int = 25,
        cursor: str | None = None,
        sort: str = "name_asc",
        q: str | None = None,
        filters: dict | None = None,  # amc, category, risk, fee_band
    ) -> FundListResponse:
        """
        List funds with cursor-based pagination, optional search, and filtering.

        Uses Elasticsearch for search if enabled, otherwise falls back to SQL.

        Args:
            limit: Number of items to return (max 100)
            cursor: Base64-encoded cursor for pagination
            sort: Sort order ('name_asc', 'name_desc', 'fee_asc', 'fee_desc', 'risk_asc', 'risk_desc')
            q: Search query string
            filters: Dictionary of filters (amc, category, risk, fee_band)

        Returns:
            FundListResponse with items, next_cursor, and metadata
        """
        # Clamp limit
        limit = min(max(1, limit), 100)
        filters = filters or {}

        # Use Elasticsearch if enabled
        if self.search_backend:
            return await self._list_funds_elasticsearch(limit, cursor, sort, q, filters)
        else:
            # Fallback to SQL (original implementation)
            return await self._list_funds_sql(limit, cursor, sort, q, filters)
    
    async def _list_funds_elasticsearch(
        self,
        limit: int,
        cursor: str | None,
        sort: str,
        q: str | None,
        filters: dict,
    ) -> FundListResponse:
        """List funds using Elasticsearch backend."""
        try:
            # Ensure index exists
            await self.search_backend.initialize_index()
            
            # Check if index has any documents
            from elasticsearch.exceptions import NotFoundError
            try:
                stats = await self.search_backend.client.indices.stats(index=self.search_backend.index_name)
                doc_count = stats["indices"][self.search_backend.index_name]["total"]["docs"]["count"]
            except (NotFoundError, KeyError):
                doc_count = 0
            
            # If index is empty, fall back to SQL (index not yet populated)
            if doc_count == 0:
                import logging
                logger = logging.getLogger(__name__)
                logger.info("Elasticsearch index is empty, falling back to SQL search")
                return await self._list_funds_sql(limit, cursor, sort, q, filters)
            
            # Search using Elasticsearch
            search_result = await self.search_backend.search(
                query=q,
                filters=filters,
                sort=sort,
                limit=limit,
                cursor=cursor,
            )
                
        except Exception as e:
            # If Elasticsearch fails, fall back to SQL
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Elasticsearch search failed, falling back to SQL: {e}")
            return await self._list_funds_sql(limit, cursor, sort, q, filters)
        
        # Convert Elasticsearch results to FundSummary
        # First, collect fund_ids to look up Fund records for return data
        fund_ids = [doc["fund_id"] for doc in search_result["items"]]
        
        # Look up Fund records to get proj_id and class_abbr_name for return data fetching
        fund_records = []
        for fund_id in fund_ids:
            # Try lookup by class_abbr_name first
            query = select(Fund).where(Fund.class_abbr_name == fund_id)
            result = await self.db.execute(query)
            fund = result.scalar_one_or_none()
            
            if not fund:
                # Fallback to proj_id
                query = select(Fund).where(Fund.proj_id == fund_id).where(Fund.class_abbr_name == "")
                result = await self.db.execute(query)
                fund = result.scalar_one_or_none()
            
            if fund:
                fund_records.append(fund)
        
        # Fetch return snapshots for all funds (US-N10, US-N13)
        return_data = await self._fetch_return_snapshots(fund_records)
        
        # Compute peer ranks for funds (US-N13)
        peer_ranks = {}
        try:
            # Get latest as-of date for peer ranking
            as_of_date = await self._get_latest_return_as_of_date()
            if as_of_date and fund_records:
                # Get unique proj_ids from fund records
                proj_ids = list(set([fund.proj_id for fund in fund_records]))
                
                # Get representative classes for all funds
                with SyncSessionLocal() as sync_session:
                    rep_class_service = RepresentativeClassService(sync_session)
                    rep_classes = rep_class_service.select_representative_classes_batch(proj_ids)
                    
                    # Build fund identifier mapping
                    fund_record_map = {}  # Maps fund_id from doc -> Fund record
                    for fund_record in fund_records:
                        fund_id = fund_record.class_abbr_name if fund_record.class_abbr_name else fund_record.proj_id
                        fund_record_map[fund_id] = fund_record
                    
                    # Build identifiers for peer ranking
                    identifiers_to_compute = []
                    doc_to_identifier = {}  # Maps doc index -> identifier
                    
                    for i, doc in enumerate(search_result["items"]):
                        fund_id = doc["fund_id"]
                        fund_record = fund_record_map.get(fund_id)
                        
                        if fund_record:
                            rep_class = rep_classes.get(fund_record.proj_id)
                            if rep_class:
                                identifier = rep_class
                            elif fund_record.class_abbr_name:
                                identifier = fund_record.class_abbr_name
                            else:
                                identifier = fund_record.proj_id
                            
                            doc_to_identifier[i] = identifier
                            if identifier not in identifiers_to_compute:
                                identifiers_to_compute.append(identifier)
                    
                    # Compute peer ranks in batch
                    ranking_service = PeerRankingService(sync_session)
                    
                    ranks_1y = ranking_service.compute_peer_ranks_batch(
                        identifiers_to_compute,
                        "1y",
                        as_of_date
                    )
                    
                    # For identifiers without 1y rank, try ytd
                    identifiers_needing_ytd = [
                        identifier for identifier in identifiers_to_compute
                        if not ranks_1y.get(identifier) or ranks_1y[identifier].percentile is None
                    ]
                    
                    ranks_ytd = {}
                    if identifiers_needing_ytd:
                        ranks_ytd = ranking_service.compute_peer_ranks_batch(
                            identifiers_needing_ytd,
                            "ytd",
                            as_of_date
                        )
                    
                    # Build mapping from doc index to peer rank
                    for i in doc_to_identifier:
                        identifier = doc_to_identifier[i]
                        rank_result = ranks_1y.get(identifier)
                        
                        if rank_result and rank_result.percentile is not None:
                            peer_ranks[i] = PeerRank.from_peer_rank_result(rank_result)
                        else:
                            rank_result_ytd = ranks_ytd.get(identifier)
                            if rank_result_ytd and rank_result_ytd.percentile is not None:
                                peer_ranks[i] = PeerRank.from_peer_rank_result(rank_result_ytd)
        except Exception as e:
            # Log error but continue without peer ranks
            logger.warning(f"Failed to compute peer ranks for Elasticsearch results: {e}", exc_info=True)
        
        items = []
        for i, doc in enumerate(search_result["items"]):
            # Find corresponding fund record for return data
            fund_id = doc["fund_id"]
            fund_record = next((f for f in fund_records if (f.class_abbr_name == fund_id) or (f.proj_id == fund_id and not f.class_abbr_name)), None)
            
            # Get return data if fund record found
            returns = {"trailing_1y_return": None, "ytd_return": None}
            if fund_record:
                fund_key = (fund_record.proj_id, fund_record.class_abbr_name if fund_record.class_abbr_name else "")
                returns = return_data.get(fund_key, returns)
            
            # Get peer rank for this fund (US-N13)
            peer_rank = peer_ranks.get(i)
            
            items.append(FundSummary(
                fund_id=doc["fund_id"],
                fund_name=doc["fund_name"],
                amc_name=doc.get("amc_name", "Unknown"),
                category=doc.get("category"),
                risk_level=doc.get("risk_level"),
                expense_ratio=float(doc["expense_ratio"]) if doc.get("expense_ratio") is not None else None,
                aimc_category=doc.get("aimc_category"),
                aimc_category_source=doc.get("aimc_category_source"),
                trailing_1y_return=returns["trailing_1y_return"],  # US-N10, US-N13
                ytd_return=returns["ytd_return"],  # US-N10, US-N13
                peer_rank=peer_rank,  # US-N13: Peer ranking data
            ))
        
        # Get snapshot info from database
        snapshot_result = await self.db.execute(
            select(Fund.data_snapshot_id, Fund.last_upd_date)
            .where(Fund.data_snapshot_id.isnot(None))
            .order_by(Fund.last_upd_date.desc())
            .limit(1)
        )
        snapshot_row = snapshot_result.first()
        
        return FundListResponse(
            items=items,
            next_cursor=search_result["next_cursor"],
            as_of_date=snapshot_row[1].strftime("%Y-%m-%d") if snapshot_row and snapshot_row[1] else datetime.now().strftime("%Y-%m-%d"),
            data_snapshot_id=snapshot_row[0] if snapshot_row else "unknown",
        )
    
    async def _list_funds_sql(
        self,
        limit: int,
        cursor: str | None,
        sort: str,
        q: str | None,
        filters: dict,
    ) -> FundListResponse:
        """List funds using SQL backend (fallback)."""
        # Base query with eager loading
        query = (
            select(Fund)
            .join(AMC, Fund.amc_id == AMC.unique_id)
            .options(selectinload(Fund.amc))
            .where(Fund.fund_status == "RG")
        )

        # Apply Filters
        if q:
            from app.utils.normalization import normalize_search_text
            q_norm = normalize_search_text(q)
            q_lower = q.lower().strip()
            # Search normalized fields first, fallback to raw fields if normalized is NULL
            query = query.where(
                or_(
                    # Normalized fields (preferred)
                    Fund.fund_name_norm.contains(q_norm),
                    Fund.fund_abbr_norm.contains(q_norm),
                    # Fallback to raw fields if normalized is NULL
                    and_(
                        Fund.fund_name_norm.is_(None),
                        or_(
                            Fund.fund_name_en.ilike(f"%{q_lower}%"),
                            Fund.fund_abbr.ilike(f"%{q_lower}%")
                        )
                    ),
                    and_(
                        Fund.fund_abbr_norm.is_(None),
                        Fund.fund_abbr.ilike(f"%{q_lower}%")
                    )
                )
            )

        if filters.get("amc"):
            query = query.where(Fund.amc_id.in_(filters["amc"]))

        if filters.get("category"):
            query = query.where(Fund.category.in_(filters["category"]))

        if filters.get("risk"):
            # Support both integer and string risk levels for backward compatibility
            risk_values = filters["risk"]
            risk_conditions = []
            for risk_val in risk_values:
                try:
                    # Try integer first (preferred)
                    risk_int = int(risk_val)
                    risk_conditions.append(Fund.risk_level_int == risk_int)
                except (ValueError, TypeError):
                    # Fallback to string matching
                    risk_conditions.append(Fund.risk_level == risk_val)
            if risk_conditions:
                query = query.where(or_(*risk_conditions))

        # Fee Band (Derived)
        # Note: Uses stored expense_ratio from database (approximate) for performance.
        # For accurate expense ratio values, use FundDetail response or /funds/{fund_id}/fees endpoint.
        fee_bands = filters.get("fee_band")
        if fee_bands:
            fee_conditions = []
            for band in fee_bands:
                if band == "low":
                    fee_conditions.append(and_(Fund.expense_ratio <= 1.0, Fund.expense_ratio.isnot(None)))
                elif band == "medium":
                    fee_conditions.append(and_(Fund.expense_ratio > 1.0, Fund.expense_ratio <= 2.0))
                elif band == "high":
                    fee_conditions.append(Fund.expense_ratio > 2.0)
            
            if fee_conditions:
                query = query.where(or_(*fee_conditions))

        # Sorting
        primary_col = None
        is_desc = False
        
        if sort == "name_desc":
            query = query.order_by(Fund.fund_name_en.desc(), Fund.proj_id.asc())
            primary_col = Fund.fund_name_en
            is_desc = True
        elif sort == "fee_asc":
            # Note: Uses stored expense_ratio from database (approximate) for performance.
            # For accurate expense ratio values, use FundDetail response or /funds/{fund_id}/fees endpoint.
            query = query.order_by(Fund.expense_ratio.asc().nullslast(), Fund.proj_id.asc())
            primary_col = Fund.expense_ratio
            is_desc = False
        elif sort == "fee_desc":
            # Note: Uses stored expense_ratio from database (approximate) for performance.
            # For accurate expense ratio values, use FundDetail response or /funds/{fund_id}/fees endpoint.
            query = query.order_by(Fund.expense_ratio.desc().nullslast(), Fund.proj_id.asc())
            primary_col = Fund.expense_ratio
            is_desc = True
        elif sort == "risk_asc":
            # Use risk_level_int for proper numeric sorting
            query = query.order_by(Fund.risk_level_int.asc().nullslast(), Fund.proj_id.asc())
            primary_col = Fund.risk_level_int
            is_desc = False
        elif sort == "risk_desc":
            # Use risk_level_int for proper numeric sorting
            query = query.order_by(Fund.risk_level_int.desc().nullslast(), Fund.proj_id.asc())
            primary_col = Fund.risk_level_int
            is_desc = True
        else:
            query = query.order_by(Fund.fund_name_en.asc(), Fund.proj_id.asc())
            primary_col = Fund.fund_name_en
            is_desc = False

        # Apply Cursor
        if cursor:
            cursor_data = self._decode_cursor(cursor)
            if cursor_data:
                c_val = cursor_data.get("v")
                c_id = cursor_data.get("i")
                
                if c_id:
                    seek_clause = None
                    
                    if c_val is None:
                        seek_clause = and_(primary_col.is_(None), Fund.proj_id > c_id)
                    else:
                        if is_desc:
                            comp_val = primary_col < c_val
                        else:
                            comp_val = primary_col > c_val
                        
                        comp_id = and_(primary_col == c_val, Fund.proj_id > c_id)
                        comp_null = primary_col.is_(None)
                        seek_clause = or_(comp_val, comp_id, comp_null)

                    query = query.where(seek_clause)

        # Execute & Fetch
        query = query.limit(limit + 1)
        result = await self.db.execute(query)
        funds = result.scalars().all()
        
        has_more = len(funds) > limit
        if has_more:
            funds = funds[:limit]

        # Fetch return snapshots for all funds (US-N10, US-N13)
        return_data = await self._fetch_return_snapshots(funds)
        
        # Compute peer ranks for funds (US-N13)
        peer_ranks = {}
        try:
            # Get latest as-of date for peer ranking
            as_of_date = await self._get_latest_return_as_of_date()
            if as_of_date:
                # Get unique proj_ids from funds
                proj_ids = list(set([fund.proj_id for fund in funds]))
                
                # Get representative classes for all funds
                with SyncSessionLocal() as sync_session:
                    rep_class_service = RepresentativeClassService(sync_session)
                    rep_classes = rep_class_service.select_representative_classes_batch(proj_ids)
                    
                    # Build fund identifier mapping: fund -> identifier for peer ranking
                    # Use representative class if available, otherwise use fund's own class_abbr_name or proj_id
                    fund_identifier_map = {}  # Maps fund index -> identifier
                    unique_identifiers = []  # List of unique identifiers to compute ranks for
                    identifier_to_funds = {}  # Maps identifier -> list of fund indices that use it
                    
                    for i, fund in enumerate(funds):
                        rep_class = rep_classes.get(fund.proj_id)
                        if rep_class:
                            identifier = rep_class
                        elif fund.class_abbr_name:
                            identifier = fund.class_abbr_name
                        else:
                            identifier = fund.proj_id
                        
                        fund_identifier_map[i] = identifier
                        
                        if identifier not in identifier_to_funds:
                            unique_identifiers.append(identifier)
                            identifier_to_funds[identifier] = []
                        identifier_to_funds[identifier].append(i)
                    
                    # Compute peer ranks in batch (horizon: 1y first)
                    ranking_service = PeerRankingService(sync_session)
                    
                    ranks_1y = ranking_service.compute_peer_ranks_batch(
                        unique_identifiers,
                        "1y",
                        as_of_date
                    )
                    
                    # For identifiers without 1y rank, try ytd
                    identifiers_needing_ytd = [
                        identifier for identifier in unique_identifiers
                        if not ranks_1y.get(identifier) or ranks_1y[identifier].percentile is None
                    ]
                    
                    ranks_ytd = {}
                    if identifiers_needing_ytd:
                        ranks_ytd = ranking_service.compute_peer_ranks_batch(
                            identifiers_needing_ytd,
                            "ytd",
                            as_of_date
                        )
                    
                    # Build mapping from fund index to peer rank
                    for i, fund in enumerate(funds):
                        identifier = fund_identifier_map[i]
                        rank_result = ranks_1y.get(identifier)
                        
                        # Use 1y if available, otherwise use ytd
                        if rank_result and rank_result.percentile is not None:
                            peer_ranks[i] = PeerRank.from_peer_rank_result(rank_result)
                        else:
                            rank_result_ytd = ranks_ytd.get(identifier)
                            if rank_result_ytd and rank_result_ytd.percentile is not None:
                                peer_ranks[i] = PeerRank.from_peer_rank_result(rank_result_ytd)
        except Exception as e:
            # Log error but continue without peer ranks
            logger.warning(f"Failed to compute peer ranks: {e}", exc_info=True)
        
        # Build Response
        items = []
        for i, fund in enumerate(funds):
            amc_name = "Unknown"
            if fund.amc:
                amc_name = fund.amc.name_en
            else:
                amc_res = await self.db.execute(select(AMC).where(AMC.unique_id == fund.amc_id))
                amc_obj = amc_res.scalar_one_or_none()
                if amc_obj:
                    amc_name = amc_obj.name_en

            # Use risk_level_int if available, fallback to risk_level string
            risk_level_display = str(fund.risk_level_int) if fund.risk_level_int is not None else fund.risk_level
            
            # Use class_abbr_name as fund_id if it exists, otherwise use proj_id
            display_fund_id = fund.class_abbr_name if fund.class_abbr_name and fund.class_abbr_name != "" else fund.proj_id
            
            # Get return data for this fund (US-N10, US-N13)
            fund_key = (fund.proj_id, fund.class_abbr_name if fund.class_abbr_name else "")
            returns = return_data.get(fund_key, {"trailing_1y_return": None, "ytd_return": None})
            
            # Get peer rank for this fund (US-N13)
            peer_rank = peer_ranks.get(i)
            
            items.append(FundSummary(
                fund_id=display_fund_id,
                fund_name=fund.fund_name_en,
                amc_name=amc_name,
                category=fund.category,
                risk_level=risk_level_display,
                aimc_category=fund.aimc_category,
                aimc_category_source=fund.aimc_category_source,
                peer_focus=fund.peer_focus,  # US-N9, US-N13: For category display
                trailing_1y_return=returns["trailing_1y_return"],  # US-N10, US-N13
                ytd_return=returns["ytd_return"],  # US-N10, US-N13
                peer_rank=peer_rank,  # US-N13: Peer ranking data
            ))

        # Build next cursor
        next_cursor = None
        if has_more and funds:
            last_fund = funds[-1]
            val = None
            if primary_col == Fund.expense_ratio:
                val = float(last_fund.expense_ratio) if last_fund.expense_ratio is not None else None
            elif primary_col == Fund.risk_level_int:
                val = last_fund.risk_level_int
            elif primary_col == Fund.risk_level:
                val = last_fund.risk_level
            elif primary_col == Fund.fund_name_en:
                val = last_fund.fund_name_en
            
            next_cursor = self._encode_cursor(val, last_fund.proj_id)

        # Get snapshot info
        snapshot_result = await self.db.execute(
            select(Fund.data_snapshot_id, Fund.last_upd_date)
            .where(Fund.data_snapshot_id.isnot(None))
            .order_by(Fund.last_upd_date.desc())
            .limit(1)
        )
        snapshot_row = snapshot_result.first()

        return FundListResponse(
            items=items,
            next_cursor=next_cursor,
            as_of_date=snapshot_row[1].strftime("%Y-%m-%d") if snapshot_row and snapshot_row[1] else datetime.now().strftime("%Y-%m-%d"),
            data_snapshot_id=snapshot_row[0] if snapshot_row else "unknown",
        )

    async def get_fund_count(self) -> int:
        """Get total count of active funds."""
        result = await self.db.execute(
            select(func.count(Fund.proj_id)).where(Fund.fund_status == "RG")
        )
        return result.scalar() or 0
    
    async def get_meta_stats(self) -> Dict[str, Any]:
        """
        Get metadata stats for home page (fund count and freshness).
        
        Uses in-memory cache with 5-minute TTL to reduce database load.
        
        Returns:
            {
                "total_fund_count": int,
                "data_as_of": str (YYYY-MM-DD),
                "data_source": str | None
            }
        """
        # Check cache
        cache_key = "meta_stats"
        current_time = time.time()
        
        if cache_key in _meta_cache:
            cached_data, cached_time = _meta_cache[cache_key]
            if current_time - cached_time < CACHE_TTL:
                return cached_data
        
        # Cache miss or expired - fetch from database
        # Get fund count
        fund_count = await self.get_fund_count()
        
        # Get freshness (same logic as list_funds)
        snapshot_result = await self.db.execute(
            select(Fund.data_snapshot_id, Fund.last_upd_date, Fund.data_source)
            .where(Fund.data_snapshot_id.isnot(None))
            .order_by(Fund.last_upd_date.desc())
            .limit(1)
        )
        snapshot_row = snapshot_result.first()
        
        # Format freshness date
        if snapshot_row and snapshot_row[1]:
            data_as_of = snapshot_row[1].strftime("%Y-%m-%d")
            data_source = snapshot_row[2] if snapshot_row[2] else None
        else:
            # Fallback to current date if no snapshot available
            data_as_of = datetime.now().strftime("%Y-%m-%d")
            data_source = None
        
        result = {
            "total_fund_count": fund_count,
            "data_as_of": data_as_of,
            "data_source": data_source
        }
        
        # Update cache
        _meta_cache[cache_key] = (result, current_time)
        
        return result

    async def get_amcs_with_fund_counts(
        self,
        search_term: str | None = None,
        limit: int = 20,
        cursor: str | None = None
    ) -> dict:
        """
        Get list of AMCs with their active fund counts, supporting search and pagination.
        
        Uses Elasticsearch aggregation if available, otherwise falls back to SQL.
        
        Args:
            search_term: Optional search term to filter AMC names
            limit: Maximum number of results (default 20, max 100)
            cursor: Base64-encoded cursor for pagination
        
        Returns:
            {
                "items": [{"id": str, "name": str, "count": int}],
                "next_cursor": str | None
            }
        """
        # Clamp limit
        limit = min(max(1, limit), 100)
        
        # Decode cursor if provided
        cursor_dict = None
        if cursor:
            cursor_dict = self._decode_amc_cursor(cursor)
        
        # Try Elasticsearch first if available
        if self.search_backend:
            try:
                # Check if ES index is populated
                from elasticsearch.exceptions import NotFoundError
                try:
                    stats = await self.search_backend.client.indices.stats(
                        index=self.search_backend.index_name
                    )
                    doc_count = stats["indices"][self.search_backend.index_name]["total"]["docs"]["count"]
                except (NotFoundError, KeyError):
                    doc_count = 0
                
                if doc_count > 0:
                    # Use ES aggregation
                    result = await self.search_backend.get_amc_aggregation(
                        search_term=search_term,
                        limit=limit,
                        cursor=cursor_dict
                    )
                    if result and result.get("items"):
                        # Encode cursor for response
                        next_cursor = None
                        if result.get("next_cursor"):
                            next_cursor = self._encode_amc_cursor(result["next_cursor"])
                        return {
                            "items": result["items"],
                            "next_cursor": next_cursor
                        }
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Elasticsearch AMC aggregation failed, falling back to SQL: {e}")
        
        # Fallback to SQL
        return await self._get_amcs_with_fund_counts_sql(search_term, limit, cursor_dict)
    
    async def _get_amcs_with_fund_counts_sql(
        self,
        search_term: str | None = None,
        limit: int = 20,
        cursor_dict: dict | None = None
    ) -> dict:
        """SQL fallback for AMC aggregation with search and pagination."""
        from sqlalchemy import or_, and_
        
        # Base query
        query = (
            select(
                AMC.unique_id,
                AMC.name_en,
                AMC.name_th,
                func.count(Fund.proj_id).label("fund_count")
            )
            .join(Fund, AMC.unique_id == Fund.amc_id)
            .where(Fund.fund_status == "RG")
            .group_by(AMC.unique_id, AMC.name_en, AMC.name_th)
        )
        
        # Add search filter if provided
        if search_term:
            search_lower = search_term.lower().strip()
            query = query.where(
                or_(
                    AMC.name_en.ilike(f"%{search_lower}%"),
                    AMC.name_th.ilike(f"%{search_lower}%")
                )
            )
        
        # Apply cursor-based pagination
        if cursor_dict:
            last_amc_id = cursor_dict.get("last_amc_id")
            last_count = cursor_dict.get("last_count")
            if last_amc_id:
                # Filter: count > last_count OR (count == last_count AND amc_id > last_amc_id)
                query = query.having(
                    or_(
                        func.count(Fund.proj_id) < last_count,
                        and_(
                            func.count(Fund.proj_id) == last_count,
                            AMC.unique_id > last_amc_id
                        )
                    )
                )
        
        # Order by count descending, then by AMC ID for deterministic ordering
        query = query.order_by(
            func.count(Fund.proj_id).desc(),
            AMC.unique_id.asc()
        )
        
        # Fetch limit + 1 to check for next page
        query = query.limit(limit + 1)
        
        result = await self.db.execute(query)
        rows = result.all()
        
        has_more = len(rows) > limit
        if has_more:
            rows = rows[:limit]
        
        items = [
            {
                "id": row.unique_id,
                "name": row.name_en or row.name_th or "Unknown",
                "count": row.fund_count
            }
            for row in rows
        ]
        
        # Build next cursor
        next_cursor = None
        if has_more and rows:
            last_row = rows[-1]
            cursor_data = {
                "last_amc_id": last_row.unique_id,
                "last_count": last_row.fund_count
            }
            next_cursor = self._encode_amc_cursor(cursor_data)
        
        return {
            "items": items,
            "next_cursor": next_cursor
        }
    
    async def get_categories_with_counts(self) -> list[dict]:
        """
        Get distinct categories with counts.
        
        Uses Elasticsearch aggregation if available, otherwise falls back to SQL.
        
        Returns:
            List of {value: str, count: int} sorted by count desc, then value asc
        """
        # Try Elasticsearch first if available
        if self.search_backend:
            try:
                # Check if ES index is populated
                from elasticsearch.exceptions import NotFoundError
                try:
                    stats = await self.search_backend.client.indices.stats(
                        index=self.search_backend.index_name
                    )
                    doc_count = stats["indices"][self.search_backend.index_name]["total"]["docs"]["count"]
                except (NotFoundError, KeyError):
                    doc_count = 0
                
                if doc_count > 0:
                    # Use ES aggregation
                    result = await self.search_backend.get_category_aggregation()
                    if result:
                        return result
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Elasticsearch category aggregation failed, falling back to SQL: {e}")
        
        # Fallback to SQL
        return await self._get_categories_with_counts_sql()
    
    async def _get_categories_with_counts_sql(self) -> list[dict]:
        """SQL fallback for category aggregation."""
        query = (
            select(
                Fund.category,
                func.count(Fund.proj_id).label("count")
            )
            .where(
                and_(
                    Fund.fund_status == "RG",
                    Fund.category.isnot(None)
                )
            )
            .group_by(Fund.category)
            .order_by(func.count(Fund.proj_id).desc(), Fund.category.asc())
        )
        
        result = await self.db.execute(query)
        rows = result.all()
        
        return [
            {"value": row.category, "count": row.count}
            for row in rows
        ]
    
    async def get_risks_with_counts(self) -> list[dict]:
        """
        Get distinct risk levels with counts.
        
        Uses Elasticsearch aggregation if available, otherwise falls back to SQL.
        
        Returns:
            List of {value: str, count: int} sorted by risk_level asc (numeric if possible)
        """
        # Try Elasticsearch first if available
        if self.search_backend:
            try:
                # Check if ES index is populated
                from elasticsearch.exceptions import NotFoundError
                try:
                    stats = await self.search_backend.client.indices.stats(
                        index=self.search_backend.index_name
                    )
                    doc_count = stats["indices"][self.search_backend.index_name]["total"]["docs"]["count"]
                except (NotFoundError, KeyError):
                    doc_count = 0
                
                if doc_count > 0:
                    # Use ES aggregation
                    result = await self.search_backend.get_risk_aggregation()
                    if result:
                        return result
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Elasticsearch risk aggregation failed, falling back to SQL: {e}")
        
        # Fallback to SQL
        return await self._get_risks_with_counts_sql()
    
    async def _get_risks_with_counts_sql(self) -> list[dict]:
        """SQL fallback for risk aggregation."""
        # Use risk_level_int for proper numeric sorting
        query = (
            select(
                Fund.risk_level_int,
                func.count(Fund.proj_id).label("count")
            )
            .where(
                and_(
                    Fund.fund_status == "RG",
                    Fund.risk_level_int.isnot(None)
                )
            )
            .group_by(Fund.risk_level_int)
            .order_by(Fund.risk_level_int.asc())
        )
        
        result = await self.db.execute(query)
        rows = result.all()
        
        # Convert to string for API response (backward compatibility)
        results = [
            {"value": str(row.risk_level_int), "count": row.count}
            for row in rows
        ]
        
        return results
    
    def _encode_amc_cursor(self, cursor_data: dict) -> str:
        """Encode AMC pagination cursor to base64 string."""
        json_str = json.dumps(cursor_data, ensure_ascii=False)
        return base64.urlsafe_b64encode(json_str.encode()).decode()
    
    def _decode_amc_cursor(self, cursor: str) -> dict | None:
        """Decode AMC pagination cursor from base64 string."""
        try:
            json_str = base64.urlsafe_b64decode(cursor.encode()).decode()
            return json.loads(json_str)
        except Exception:
            return None

    def _encode_cursor(self, val: any, fund_id: str) -> str:
        """Encode cursor data to base64 string."""
        data = {"v": val, "i": fund_id}
        json_str = json.dumps(data, ensure_ascii=False)
        return base64.urlsafe_b64encode(json_str.encode()).decode()

    def _decode_cursor(self, cursor: str) -> dict | None:
        """Decode cursor from base64 string."""
        try:
            json_str = base64.urlsafe_b64decode(cursor.encode()).decode()
            return json.loads(json_str)
        except Exception:
            return None
    
    async def get_fund_by_id(self, fund_id: str):
        """
        Get detailed fund information by fund_id.
        
        Args:
            fund_id: Unique fund identifier (proj_id or class_abbr_name)
                    - If class_abbr_name (e.g., "K-INDIA-A(A)"), looks up by class
                    - Otherwise, looks up by proj_id
            
        Returns:
            FundDetail object with fund information
            
        Raises:
            ValueError: If fund_id is invalid or fund not found
        """
        import time
        from app.models.fund import FundDetail
        
        start_time = time.time()
        
        # Basic validation: fund_id must be non-empty
        if not fund_id or not fund_id.strip():
            raise ValueError("fund_id cannot be empty")
        
        fund_id = fund_id.strip()
        
        # Optimized lookup: Try class_abbr_name first, then proj_id
        # Eagerly load AMC relationship to avoid lazy loading issues in async context
        query = select(Fund).options(selectinload(Fund.amc)).where(Fund.class_abbr_name == fund_id)
        result = await self.db.execute(query)
        fund = result.scalar_one_or_none()
        
        # If not found by class name, try proj_id (backward compatibility)
        if fund is None:
            # Try fund-level record first (no classes), then any share class
            query = (
                select(Fund)
                .options(selectinload(Fund.amc))
                .where(Fund.proj_id == fund_id)
                .order_by(
                    # Prefer fund-level records (empty class_abbr_name) first
                    case((Fund.class_abbr_name == "", 0), else_=1).asc(),
                    Fund.class_abbr_name.asc()
                )
                .limit(1)
            )
            result = await self.db.execute(query)
            fund = result.scalar_one_or_none()
        
        if fund is None:
            raise ValueError(f"Fund not found: {fund_id}")
        
        # Get AMC name - relationship is eagerly loaded, so this is fast
        amc_name = "Unknown"
        if fund.amc:
            amc_name = fund.amc.name_en
        else:
            # Fallback: query AMC directly (should be rare)
            amc_res = await self.db.execute(select(AMC).where(AMC.unique_id == fund.amc_id))
            amc_obj = amc_res.scalar_one_or_none()
            if amc_obj:
                amc_name = amc_obj.name_en
        
        # Use class_abbr_name as fund_id if it exists, otherwise use proj_id
        display_fund_id = fund.class_abbr_name if fund.class_abbr_name and fund.class_abbr_name != "" else fund.proj_id
        
        # Get actual expense ratio from cached fee data (matching what fund detail page shows)
        # Note: expense_ratio field is not displayed in UI, but we calculate it here for API response
        # Optimize: Use stored expense_ratio directly - skip calculation to improve performance
        # The expense_ratio is already calculated and stored during ingestion
        expense_ratio = None
        if fund.expense_ratio is not None:
            # Use stored expense_ratio as primary source (fastest - no calculation needed)
            expense_ratio = round(float(fund.expense_ratio), 3)
        # Skip expensive fee_data_raw calculation - if expense_ratio is not stored,
        # it means the calculation failed during ingestion, so don't retry here
        
        # Format dates
        as_of_date = None
        if fund.last_upd_date:
            as_of_date = fund.last_upd_date.strftime("%Y-%m-%d")
        
        last_updated_at = None
        if fund.last_upd_date:
            last_updated_at = fund.last_upd_date.isoformat()
        
        # Ensure at least one freshness field is present
        if not as_of_date and not last_updated_at:
            # Fallback to current date if no date available
            as_of_date = datetime.now().strftime("%Y-%m-%d")
            last_updated_at = datetime.now().isoformat()
        
        # Use risk_level_int if available, fallback to risk_level string
        risk_level_display = str(fund.risk_level_int) if fund.risk_level_int is not None else fund.risk_level
        
        # AIMC Classification (with remark if from SEC_API)
        aimc_category = fund.aimc_category
        aimc_category_source = fund.aimc_category_source
        
        # Investment constraints - read from database (stored during ingestion)
        # This eliminates live API calls and significantly improves page load performance
        # Fallback to live API calls only if data is not available in database
        min_investment = None
        min_redemption = None
        min_balance = None
        redemption_period = None
        
        # Process investment constraints data from database
        investment_data = None
        if fund.investment_data_raw:
            # Data is stored as a list (one per class), get the first item or match by class
            investment_list = fund.investment_data_raw if isinstance(fund.investment_data_raw, list) else [fund.investment_data_raw]
            if investment_list:
                # Try to find matching class, otherwise use first item
                if fund.class_abbr_name:
                    investment_data = next(
                        (item for item in investment_list if item.get('class_abbr_name') == fund.class_abbr_name),
                        investment_list[0] if investment_list else None
                    )
                else:
                    investment_data = investment_list[0]
        
        # If not in database, try live API call as fallback
        if not investment_data:
            try:
                investment_data = await self._get_investment_constraints(fund.proj_id)
            except Exception:
                pass
        
        if investment_data:
            # Format minimum investment (SEC API returns code for currency, default to THB)
            if investment_data.get('minimum_sub'):
                amount = investment_data['minimum_sub']
                min_investment = f"{self._format_currency_amount(amount)} THB"
            # Format minimum redemption
            if investment_data.get('minimum_redempt'):
                amount = investment_data['minimum_redempt']
                min_redemption = f"{self._format_currency_amount(amount)} THB"
            # Format minimum balance (value or units)
            if investment_data.get('lowbal_val') is not None and investment_data.get('lowbal_val') > 0:
                amount = investment_data['lowbal_val']
                min_balance = f"{self._format_currency_amount(amount)} THB"
            elif investment_data.get('lowbal_unit') is not None and investment_data.get('lowbal_unit') > 0:
                units = investment_data['lowbal_unit']
                min_balance = f"{self._format_currency_amount(units)} units"
        
        # Process redemption period data from database
        redemption_data = fund.redemption_data_raw
        
        # If not in database, try live API call as fallback
        if not redemption_data:
            try:
                redemption_data = await self._get_redemption_data(fund.proj_id)
            except Exception:
                pass
        
        if redemption_data:
            redemption_period = self._format_redemption_period(redemption_data)
        
        # Process dividend policy data from database (2.5)
        dividend_policy = None
        dividend_policy_remark = None
        dividend_data = None
        
        if fund.dividend_data_raw:
            # Data is stored as a list (one per class)
            dividend_list = fund.dividend_data_raw if isinstance(fund.dividend_data_raw, list) else [fund.dividend_data_raw]
            if dividend_list:
                # Try to find matching class, otherwise use first item
                if fund.class_abbr_name:
                    dividend_data = next(
                        (item for item in dividend_list if item.get('class_abbr_name') == fund.class_abbr_name),
                        dividend_list[0] if dividend_list else None
                    )
                else:
                    dividend_data = dividend_list[0]
        
        # If not in database, try live API call as fallback
        if not dividend_data:
            try:
                dividend_data = await self._get_dividend_data(fund.proj_id, fund.class_abbr_name)
            except Exception:
                pass
        
        if dividend_data:
            dividend_policy = dividend_data.get('dividend_policy')
            dividend_policy_remark = dividend_data.get('dividend_policy_remark')
        
        # Process fund policy data from database (2.3)
        fund_policy_type = None
        management_style = None
        management_style_desc = None
        policy_data = fund.policy_data_raw
        
        # If not in database, try live API call as fallback
        if not policy_data:
            try:
                policy_data = await self._get_policy_data(fund.proj_id)
            except Exception:
                pass
        
        if policy_data:
            fund_policy_type = policy_data.get('policy_desc')
            management_style = policy_data.get('management_style')
            management_style_desc = self._format_management_style(management_style)
        
        elapsed = time.time() - start_time
        if elapsed > 0.1:  # Log if takes more than 100ms
            logger.info(f"get_fund_by_id({fund_id}) took {elapsed:.3f}s")
        
        return FundDetail(
            fund_id=display_fund_id,
            fund_name=fund.fund_name_en,
            fund_abbr=fund.fund_abbr,
            category=fund.category,
            amc_id=fund.amc_id,
            amc_name=amc_name,
            risk_level=risk_level_display,
            expense_ratio=expense_ratio,
            aimc_category=aimc_category,
            aimc_category_source=aimc_category_source,
            min_investment=min_investment,
            min_redemption=min_redemption,
            min_balance=min_balance,
            redemption_period=redemption_period,
            fund_policy_type=fund_policy_type,
            management_style=management_style,
            management_style_desc=management_style_desc,
            dividend_policy=dividend_policy,
            dividend_policy_remark=dividend_policy_remark,
            proj_id=fund.proj_id,
            class_abbr_name=fund.class_abbr_name if fund.class_abbr_name else None,
            as_of_date=as_of_date,
            last_updated_at=last_updated_at,
            data_source=fund.data_source,  # Now available from schema
            data_version=fund.data_snapshot_id,
        )
    
    async def _get_investment_constraints(self, proj_id: str) -> dict | None:
        """
        Fetch investment constraints from SEC API.
        
        Args:
            proj_id: Fund project ID
            
        Returns:
            Dictionary with investment constraints or None if unavailable
        """
        from app.utils.sec_api_client import SECAPIClient
        
        try:
            client = SECAPIClient()
            data_list, error = client.fetch_investment(proj_id)
            if data_list and not error and len(data_list) > 0:
                # Return first item (or could implement class selection)
                return data_list[0]
        except Exception:
            pass
        return None
    
    async def _get_redemption_data(self, proj_id: str) -> dict | None:
        """
        Fetch redemption data from SEC API.
        
        Args:
            proj_id: Fund project ID
            
        Returns:
            Dictionary with redemption data or None if unavailable
        """
        from app.utils.sec_api_client import SECAPIClient
        
        try:
            client = SECAPIClient()
            data, error = client.fetch_redemption(proj_id)
            if data and not error:
                return data
        except Exception:
            pass
        return None
    
    @staticmethod
    def _format_redemption_period(redemption_data: dict) -> str | None:
        """
        Format redemption period for display.
        
        SEC API redemp_period codes:
        1 = Every business day
        2 = Every week
        3 = Every 2 weeks
        4 = Every month
        5 = Every quarter
        6 = Every 6 months
        7 = Every year
        8 = At maturity
        9 = Other (see redemp_period_oth)
        E = Not specified
        T = According to conditions
        """
        REDEMPTION_PERIOD_MAP = {
            '1': 'Every business day',
            '2': 'Weekly',
            '3': 'Every 2 weeks',
            '4': 'Monthly',
            '5': 'Quarterly',
            '6': 'Every 6 months',
            '7': 'Annually',
            '8': 'At maturity',
            'E': 'Not specified',
            'T': 'Per fund conditions',
        }
        
        period_code = redemption_data.get('redemp_period')
        if not period_code or period_code == '-':
            return None
        
        if period_code == '9':
            # Use the "other" description
            other_desc = redemption_data.get('redemp_period_oth')
            if other_desc and other_desc != '-':
                return other_desc
            return 'Other'
        
        return REDEMPTION_PERIOD_MAP.get(period_code, period_code)
    
    @staticmethod
    def _format_currency_amount(amount: str | float | int) -> str:
        """
        Format currency amount for display with thousand separators.
        
        Args:
            amount: Amount as string, float, or int
            
        Returns:
            Formatted string with thousand separators
        """
        try:
            # Convert to float first
            num = float(amount)
            # Format with thousand separators, no decimals if whole number
            if num == int(num):
                return f"{int(num):,}"
            else:
                return f"{num:,.2f}"
        except (ValueError, TypeError):
            return str(amount)
    
    @staticmethod
    def _calculate_fee_band(expense_ratio: Decimal | None) -> str | None:
        """
        Calculate fee band from expense ratio.
        
        Args:
            expense_ratio: Expense ratio as Decimal or None
            
        Returns:
            'low' (<=1.0%), 'medium' (1-2%), 'high' (>2%), or None
        """
        if expense_ratio is None:
            return None
        
        ratio = float(expense_ratio)
        if ratio <= 1.0:
            return "low"
        elif ratio <= 2.0:
            return "medium"
        else:
            return "high"
    
    async def _get_dividend_data(self, proj_id: str, class_abbr_name: str | None = None) -> dict | None:
        """
        Fetch dividend/distribution data from SEC API.
        
        Args:
            proj_id: Fund project ID
            class_abbr_name: Optional share class abbreviation to filter by
            
        Returns:
            Dictionary with dividend data for the specified class or None
        """
        from app.utils.sec_api_client import SECAPIClient
        
        try:
            client = SECAPIClient()
            data_list, error = client.fetch_dividend(proj_id)
            if data_list and not error and len(data_list) > 0:
                # If class specified, find matching class data
                if class_abbr_name:
                    for item in data_list:
                        if item.get('class_abbr_name') == class_abbr_name:
                            return item
                # Return first item if no class match or no class specified
                return data_list[0]
        except Exception:
            pass
        return None
    
    async def _get_policy_data(self, proj_id: str) -> dict | None:
        """
        Fetch fund policy data from SEC API.
        
        Args:
            proj_id: Fund project ID
            
        Returns:
            Dictionary with policy data or None if unavailable
        """
        from app.utils.sec_api_client import SECAPIClient
        
        try:
            client = SECAPIClient()
            data, error = client.fetch_policy(proj_id)
            if data and not error:
                return data
        except Exception:
            pass
        return None
    
    @staticmethod
    def _format_management_style(style_code: str | None) -> str | None:
        """
        Format management style code to human-readable description.
        
        SEC API management_style codes:
        AN = Active management
        PN = Passive management (index-tracking)
        """
        if not style_code:
            return None
        
        STYLE_MAP = {
            'AN': 'Active',
            'PN': 'Passive (Index-tracking)',
        }
        return STYLE_MAP.get(style_code, style_code)
    
    async def get_share_classes(self, fund_id: str) -> dict:
        """
        Get all share classes for a fund.
        
        Args:
            fund_id: Fund ID (class_abbr_name or proj_id)
            
        Returns:
            Dictionary with share class information
        """
        from app.models.fund import ShareClassInfo, ShareClassListResponse
        from app.utils.sec_api_client import SECAPIClient
        
        # First, find the fund to get its proj_id
        fund = await self._get_fund_record(fund_id)
        if not fund:
            raise ValueError(f"Fund not found: {fund_id}")
        
        proj_id = fund.proj_id
        current_class = fund.class_abbr_name or ""
        
        # Build dividend map from cached database data first (stored during ingestion)
        # This eliminates live API calls and significantly improves page load performance
        # Fallback to live API calls only if data is not available in database
        dividend_map = {}
        dividend_data_list = None
        
        # Try to get dividend data from database (check all funds with same proj_id)
        if fund.dividend_data_raw:
            dividend_data_list = fund.dividend_data_raw if isinstance(fund.dividend_data_raw, list) else [fund.dividend_data_raw]
            for div in dividend_data_list:
                class_name = div.get('class_abbr_name', '')
                dividend_map[class_name] = div.get('dividend_policy')
        
        # If not in database, try live API call as fallback
        if not dividend_data_list:
            try:
                client = SECAPIClient()
                dividend_data_list, _ = client.fetch_dividend(proj_id)
                if dividend_data_list:
                    for div in dividend_data_list:
                        class_name = div.get('class_abbr_name', '')
                        dividend_map[class_name] = div.get('dividend_policy')
            except Exception:
                pass
        
        # Try to get share classes from database first (all funds with same proj_id)
        # This eliminates live API calls and significantly improves page load performance
        classes = []
        classes_from_db = False
        
        query = select(Fund).where(
            and_(
                Fund.proj_id == proj_id,
                Fund.fund_status == "RG"  # Only active funds
            )
        ).order_by(Fund.class_abbr_name)
        
        result = await self.db.execute(query)
        db_funds = list(result.scalars().all())
        
        if len(db_funds) > 1 or (len(db_funds) == 1 and db_funds[0].class_abbr_name):
            # We have share classes in database
            classes_from_db = True
            for db_fund in db_funds:
                class_abbr = db_fund.class_abbr_name or ""
                classes.append(ShareClassInfo(
                    class_abbr_name=class_abbr or fund_id,
                    class_name=None,  # Not stored in DB, would need API for this
                    class_description=None,  # Not stored in DB, would need API for this
                    is_current=(class_abbr == current_class),
                    dividend_policy=dividend_map.get(class_abbr),
                ))
        
        # If not found in database or need additional metadata, fallback to SEC API
        if not classes_from_db:
            try:
                client = SECAPIClient()
                classes_data, error = client.fetch_class_fund(proj_id)
                
                if classes_data and not error:
                    for cls in classes_data:
                        class_abbr = cls.get('class_abbr_name', '')
                        classes.append(ShareClassInfo(
                            class_abbr_name=class_abbr,
                            class_name=cls.get('class_name'),
                            class_description=cls.get('class_additional_desc'),
                            is_current=(class_abbr == current_class),
                            dividend_policy=dividend_map.get(class_abbr),
                        ))
            except Exception:
                pass
        
        # If still no classes, create single entry for current fund
        if not classes:
            classes.append(ShareClassInfo(
                class_abbr_name=current_class or fund_id,
                class_name=None,
                class_description=None,
                is_current=True,
                dividend_policy=dividend_map.get(current_class),
            ))
        
        return {
            "proj_id": proj_id,
            "fund_name": fund.fund_name_en,
            "current_class": current_class or fund_id,
            "classes": classes,
            "total_classes": len(classes),
        }
    
    async def get_fee_breakdown(self, fund_id: str) -> dict:
        """
        Get detailed fee breakdown for a fund.
        
        Args:
            fund_id: Fund ID (class_abbr_name or proj_id)
            
        Returns:
            Dictionary with fee breakdown by section
        """
        from app.models.fund import FeeBreakdownItem, FeeBreakdownSection
        from app.utils.sec_api_client import SECAPIClient
        
        # Find the fund to get its proj_id and class
        fund = await self._get_fund_record(fund_id)
        if not fund:
            raise ValueError(f"Fund not found: {fund_id}")
        
        proj_id = fund.proj_id
        class_abbr_name = fund.class_abbr_name or ""
        
        # Process fee data from database first (stored during ingestion)
        # This eliminates live API calls and significantly improves page load performance
        # Fallback to live API calls only if data is not available in database
        fees_data = None
        error = None
        
        if fund.fee_data_raw:
            # Data is stored as a list (one per class), use it directly
            fees_data = fund.fee_data_raw if isinstance(fund.fee_data_raw, list) else [fund.fee_data_raw]
            logger.info(f"Fee breakdown for {fund_id}: Using cached fee_data_raw from database, fees_count={len(fees_data) if fees_data else 0}")
        else:
            # If not in database, try live API call as fallback
            try:
                client = SECAPIClient()
                fees_data, error = client.fetch_fees(proj_id)
                logger.info(f"Fee breakdown for {fund_id}: Fetched from SEC API, fees_count={len(fees_data) if fees_data else 0}, error={error}")
            except Exception as e:
                logger.warning(f"Failed to fetch fees from SEC API for {fund_id}: {e}")
                error = str(e)
        
        if not fees_data or error:
            return {
                "fund_id": fund_id,
                "class_abbr_name": class_abbr_name or None,
                "sections": [],
                "total_expense_ratio": float(fund.expense_ratio) if fund.expense_ratio else None,
                "total_expense_ratio_actual": None,
                "last_upd_date": None,
            }
        
        # Filter fees for current class
        # Try exact match first, then try matching without empty string issues
        class_fees = [f for f in fees_data if f.get('class_abbr_name') == class_abbr_name]
        
        # If no exact match and we have a class name, try partial matching
        if not class_fees and class_abbr_name:
            class_fees = [f for f in fees_data if class_abbr_name in (f.get('class_abbr_name') or '')]
        
        # If still no match, use all fees (fund may not have class-specific fees)
        if not class_fees:
            class_fees = fees_data
        
        logger.info(f"Filtered fees for class '{class_abbr_name}': {len(class_fees)} fees")
        
        # Categorize fees into transaction and recurring
        transaction_fees = []
        recurring_fees = []
        total_expense = None
        total_expense_actual = None
        last_upd_date = None
        
        # Fee type mappings - use contains matching for flexibility
        FEE_TYPE_MAPPINGS = [
            ('ค่าธรรมเนียมการขายหน่วยลงทุน', 'front_end_fee', 'Front-end Fee'),
            ('ค่าธรรมเนียมการรับซื้อคืนหน่วยลงทุน', 'back_end_fee', 'Back-end Fee'),
            ('ค่าธรรมเนียมการสับเปลี่ยนหน่วยลงทุนเข้า', 'switch_in_fee', 'Switching In Fee'),
            ('ค่าธรรมเนียมการสับเปลี่ยนหน่วยลงทุนออก', 'switch_out_fee', 'Switching Out Fee'),
            ('ค่าธรรมเนียมการโอนหน่วยลงทุน', 'transfer_fee', 'Transfer Fee'),
            ('ค่าธรรมเนียมการจัดการ', 'management_fee', 'Management Fee'),
            ('ค่าธรรมเนียมนายทะเบียน', 'registrar_fee', 'Registrar Fee'),
            ('ค่าธรรมเนียมผู้ดูแลผลประโยชน์', 'custodian_fee', 'Custodian Fee'),
            ('ค่าใช้จ่ายอื่น', 'other_expenses', 'Other Expenses'),
            ('ค่าธรรมเนียมและค่าใช้จ่ายรวม', 'total_fees', 'Total Fees & Expenses'),
        ]
        
        TRANSACTION_FEE_TYPES = {'front_end_fee', 'back_end_fee', 'switch_in_fee', 'switch_out_fee', 'transfer_fee'}
        
        def match_fee_type(fee_desc: str) -> tuple | None:
            """Match fee description to fee type using contains matching."""
            fee_desc_clean = fee_desc.strip() if fee_desc else ''
            for pattern, fee_type, fee_type_en in FEE_TYPE_MAPPINGS:
                if pattern in fee_desc_clean:
                    return (fee_type, fee_type_en)
            return None
        
        # Track seen fee types to avoid duplicates
        seen_fee_types = set()
        
        for fee in class_fees:
            fee_desc = fee.get('fee_type_desc', '')
            mapping = match_fee_type(fee_desc)
            
            if not mapping:
                continue
            
            fee_type, fee_type_en = mapping
            
            # Skip duplicates (same fee type might appear multiple times)
            if fee_type in seen_fee_types and fee_type != 'total_fees':
                continue
            seen_fee_types.add(fee_type)
            
            # Track last update date
            if fee.get('last_upd_date'):
                last_upd_date = fee.get('last_upd_date')
            
            # Handle total expense ratio separately
            if fee_type == 'total_fees':
                try:
                    rate_str = fee.get('rate', '')
                    if rate_str and rate_str != '-':
                        # Remove % and any whitespace
                        rate_clean = rate_str.replace('%', '').strip()
                        total_expense = float(rate_clean)
                    actual_str = fee.get('actual_value', '')
                    if actual_str and actual_str != '-':
                        actual_clean = actual_str.replace('%', '').strip()
                        total_expense_actual = float(actual_clean)
                except (ValueError, AttributeError, TypeError):
                    pass
                continue
            
            fee_item = FeeBreakdownItem(
                fee_type=fee_type,
                fee_type_desc=fee_desc,
                fee_type_desc_en=fee_type_en,
                rate=fee.get('rate'),
                rate_unit=fee.get('rate_unit'),
                actual_value=fee.get('actual_value'),
                actual_value_unit=fee.get('actual_value_unit'),
            )
            
            if fee_type in TRANSACTION_FEE_TYPES:
                transaction_fees.append(fee_item)
            else:
                recurring_fees.append(fee_item)
        
        sections = []
        if transaction_fees:
            sections.append(FeeBreakdownSection(
                section_key='transaction',
                section_label='Transaction Fees',
                fees=transaction_fees,
            ))
        if recurring_fees:
            sections.append(FeeBreakdownSection(
                section_key='recurring',
                section_label='Recurring Fees',
                fees=recurring_fees,
            ))
        
        logger.info(f"Fee breakdown result: {len(transaction_fees)} transaction, {len(recurring_fees)} recurring, total_expense={total_expense}")
        
        # Calculate fallback expense ratio from fee_data_raw if available (more accurate than stored expense_ratio)
        fallback_expense_ratio = None
        if not total_expense and fund.fee_data_raw and isinstance(fund.fee_data_raw, list):
            from app.utils.fee_calculator import calculate_expense_ratio
            try:
                calculated = calculate_expense_ratio(fund.fee_data_raw, class_abbr=class_abbr_name)
                if calculated is not None:
                    fallback_expense_ratio = float(calculated)
            except Exception:
                pass
        
        return {
            "fund_id": fund_id,
            "class_abbr_name": class_abbr_name or None,
            "sections": sections,
            "total_expense_ratio": total_expense or fallback_expense_ratio or (float(fund.expense_ratio) if fund.expense_ratio else None),
            "total_expense_ratio_actual": total_expense_actual,
            "last_upd_date": last_upd_date,
        }
    
    async def _get_latest_return_as_of_date(self) -> date | None:
        """
        Get the latest as-of date from return snapshots.
        
        Returns:
            Latest as-of date as date object, or None if no snapshots exist
        """
        result = await self.db.execute(
            select(FundReturnSnapshot.as_of_date)
            .order_by(desc(FundReturnSnapshot.as_of_date))
            .limit(1)
        )
        row = result.first()
        return row[0] if row else None
    
    async def _fetch_return_snapshots(
        self, 
        funds: list[Fund]
    ) -> dict[tuple[str, str], dict[str, float | None]]:
        """
        Fetch latest return snapshots for a list of funds.
        
        Uses a single batch query with window function to get latest snapshot per fund/class.
        
        Args:
            funds: List of Fund ORM objects
            
        Returns:
            Dict mapping (proj_id, class_abbr_name) to dict with trailing_1y_return and ytd_return
        """
        if not funds:
            return {}
        
        # Build list of (proj_id, class_abbr_name) tuples
        # Normalize: empty string and "main" are equivalent for return snapshots
        fund_keys = [
            (fund.proj_id, fund.class_abbr_name if fund.class_abbr_name else "")
            for fund in funds
        ]
        
        # Initialize return data with None values
        return_data = {key: {"trailing_1y_return": None, "ytd_return": None} for key in fund_keys}
        
        # Build conditions for all fund/class combinations
        # If class_abbr_name is empty, also try "main" and "Main" (common in return snapshots)
        conditions = []
        for proj_id, class_abbr_name in fund_keys:
            if not class_abbr_name:
                # Empty class: try "", "main", and "Main"
                conditions.append(
                    and_(
                        FundReturnSnapshot.proj_id == proj_id,
                        or_(
                            FundReturnSnapshot.class_abbr_name == "",
                            FundReturnSnapshot.class_abbr_name == "main",
                            FundReturnSnapshot.class_abbr_name == "Main"
                        )
                    )
                )
            else:
                conditions.append(
                    and_(
                        FundReturnSnapshot.proj_id == proj_id,
                        FundReturnSnapshot.class_abbr_name == class_abbr_name
                    )
                )
        
        if not conditions:
            return return_data
        
        # Use window function to get latest snapshot per fund/class in a single query
        from sqlalchemy import distinct, case
        
        # Subquery to rank snapshots by date per fund/class
        ranked_snapshots = (
            select(
                FundReturnSnapshot.proj_id,
                FundReturnSnapshot.class_abbr_name,
                FundReturnSnapshot.trailing_1y_return,
                FundReturnSnapshot.ytd_return,
                func.row_number()
                .over(
                    partition_by=[FundReturnSnapshot.proj_id, FundReturnSnapshot.class_abbr_name],
                    order_by=FundReturnSnapshot.as_of_date.desc()
                )
                .label("rn")
            )
            .where(or_(*conditions))
            .subquery()
        )
        
        # Get only the latest snapshot (rn=1) for each fund/class
        latest_snapshots_query = (
            select(
                ranked_snapshots.c.proj_id,
                ranked_snapshots.c.class_abbr_name,
                ranked_snapshots.c.trailing_1y_return,
                ranked_snapshots.c.ytd_return,
            )
            .where(ranked_snapshots.c.rn == 1)
        )
        
        result = await self.db.execute(latest_snapshots_query)
        rows = result.all()
        
        # Map results to return_data
        # Normalize "main" and "Main" back to "" for matching with fund_keys
        for row in rows:
            # Normalize class_abbr_name: "main" or "Main" -> "" to match fund_keys
            normalized_class = "" if row.class_abbr_name in ("main", "Main") else row.class_abbr_name
            key = (row.proj_id, normalized_class)
            if key in return_data:
                return_data[key] = {
                    "trailing_1y_return": float(row.trailing_1y_return) if row.trailing_1y_return is not None else None,
                    "ytd_return": float(row.ytd_return) if row.ytd_return is not None else None,
                }
        
        return return_data
    
    async def _get_fund_record(self, fund_id: str):
        """
        Get fund ORM record by fund_id.
        
        Args:
            fund_id: Fund ID (class_abbr_name or proj_id)
            
        Returns:
            Fund ORM object or None
        """
        # Try lookup by class_abbr_name first
        query = select(Fund).where(Fund.class_abbr_name == fund_id)
        result = await self.db.execute(query)
        fund = result.scalar_one_or_none()
        
        if not fund:
            # Fallback to proj_id
            query = select(Fund).where(Fund.proj_id == fund_id).where(Fund.class_abbr_name == "")
            result = await self.db.execute(query)
            fund = result.scalar_one_or_none()
        
        return fund
