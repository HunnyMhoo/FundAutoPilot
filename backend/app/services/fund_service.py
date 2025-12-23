"""Fund service for business logic operations."""

import base64
import json
import time
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.models.fund_orm import Fund, AMC
from app.models.fund import FundSummary, FundListResponse, CursorData
from app.services.search.elasticsearch_backend import ElasticsearchSearchBackend
from app.core.elasticsearch import get_elasticsearch_client

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
        items = []
        for doc in search_result["items"]:
            items.append(FundSummary(
                fund_id=doc["fund_id"],
                fund_name=doc["fund_name"],
                amc_name=doc.get("amc_name", "Unknown"),
                category=doc.get("category"),
                risk_level=doc.get("risk_level"),
                expense_ratio=float(doc["expense_ratio"]) if doc.get("expense_ratio") is not None else None,
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
            query = query.order_by(Fund.expense_ratio.asc().nullslast(), Fund.proj_id.asc())
            primary_col = Fund.expense_ratio
            is_desc = False
        elif sort == "fee_desc":
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

        # Build Response
        items = []
        for fund in funds:
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
            
            items.append(FundSummary(
                fund_id=fund.proj_id,
                fund_name=fund.fund_name_en,
                amc_name=amc_name,
                category=fund.category,
                risk_level=risk_level_display,
                expense_ratio=float(fund.expense_ratio) if fund.expense_ratio is not None else None,
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
            fund_id: Unique fund identifier (proj_id)
            
        Returns:
            FundDetail object with fund information
            
        Raises:
            ValueError: If fund_id is invalid or fund not found
        """
        from app.models.fund import FundDetail
        
        # Basic validation: fund_id must be non-empty
        if not fund_id or not fund_id.strip():
            raise ValueError("fund_id cannot be empty")
        
        # Query fund with AMC relationship
        query = (
            select(Fund)
            .join(AMC, Fund.amc_id == AMC.unique_id)
            .options(selectinload(Fund.amc))
            .where(Fund.proj_id == fund_id.strip())
        )
        
        result = await self.db.execute(query)
        fund = result.scalar_one_or_none()
        
        if fund is None:
            raise ValueError(f"Fund not found: {fund_id}")
        
        # Get AMC name
        amc_name = "Unknown"
        if fund.amc:
            amc_name = fund.amc.name_en
        else:
            # Fallback: query AMC directly
            amc_res = await self.db.execute(select(AMC).where(AMC.unique_id == fund.amc_id))
            amc_obj = amc_res.scalar_one_or_none()
            if amc_obj:
                amc_name = amc_obj.name_en
        
        # Format expense_ratio to 3 decimals if present
        expense_ratio = None
        if fund.expense_ratio is not None:
            expense_ratio = round(float(fund.expense_ratio), 3)
        
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
        
        return FundDetail(
            fund_id=fund.proj_id,
            fund_name=fund.fund_name_en,
            fund_abbr=fund.fund_abbr,
            category=fund.category,
            amc_id=fund.amc_id,
            amc_name=amc_name,
            risk_level=risk_level_display,
            expense_ratio=expense_ratio,
            as_of_date=as_of_date,
            last_updated_at=last_updated_at,
            data_source=fund.data_source,  # Now available from schema
            data_version=fund.data_snapshot_id,
        )
    
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
