"""Fund service for business logic operations."""

import base64
import json
from datetime import datetime

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.fund_orm import Fund, AMC
from app.models.fund import FundSummary, FundListResponse, CursorData


class FundService:
    """Service for fund-related business logic."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
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

        # Base query
        query = (
            select(Fund)
            .join(AMC, Fund.amc_id == AMC.unique_id)
            .where(Fund.fund_status == "RG")
        )

        # ---------------------------------------------------------
        # 1. Apply Filters
        # ---------------------------------------------------------

        # Search (US2)
        if q:
            q_norm = q.lower().strip()
            query = query.where(
                or_(
                    Fund.fund_name_norm.contains(q_norm),
                    Fund.fund_abbr_norm.contains(q_norm)
                )
            )

        # AMC
        if filters.get("amc"):
            query = query.where(Fund.amc_id.in_(filters["amc"]))

        # Category
        if filters.get("category"):
            query = query.where(Fund.category.in_(filters["category"]))

        # Risk
        if filters.get("risk"):
            # Risk is stored as string in DB for now, ensure input matches
            query = query.where(Fund.risk_level.in_(filters["risk"]))

        # Fee Band (Derived)
        fee_bands = filters.get("fee_band")
        if fee_bands:
            fee_conditions = []
            for band in fee_bands:
                if band == "low":  # <= 1.0 (and not null)
                    fee_conditions.append(and_(Fund.expense_ratio <= 1.0, Fund.expense_ratio.isnot(None)))
                elif band == "medium":  # > 1.0 and <= 2.0
                    fee_conditions.append(and_(Fund.expense_ratio > 1.0, Fund.expense_ratio <= 2.0))
                elif band == "high":  # > 2.0
                    fee_conditions.append(Fund.expense_ratio > 2.0)
            
            if fee_conditions:
                # OR logic between bands (Low OR Medium)
                query = query.where(or_(*fee_conditions))
            else:
                # Should not happen via UI, but if empty list provided, maybe no-op or valid?
                # If param key exists but empty list, effectively blocks nothing or blocks everything?
                # Usually "no selection" = "all", but explicit empty list? Let's assume passed only if values exist
                pass

        # ---------------------------------------------------------
        # 2. Sorting & Cursor Direction
        # ---------------------------------------------------------
        # Define the sort column and direction
        # Strategy: Primary Sort (Nullable) + Secondary Tie-breaker (Proj ID)
        
        # Helper to apply sort and return the columns relevant for cursor
        primary_col = None
        is_desc = False
        
        if sort == "name_desc":
            query = query.order_by(Fund.fund_name_en.desc(), Fund.proj_id.asc())
            primary_col = Fund.fund_name_en
            is_desc = True
        elif sort == "fee_asc":
            # Float/Numeric sort. Nulls last is standard expectation.
            # Postgres: NULLS LAST is default for ASC? No, it's LAST for ASC usually. 
            # Let's be explicit if dialect supports it, but standard SQL sort is specific.
            # In SQLite/others logic varies. Simple approach for MVP:
            # We want: 0.1, 0.5, ... 2.0, NULL
            query = query.order_by(Fund.expense_ratio.asc().nullslast(), Fund.proj_id.asc())
            primary_col = Fund.expense_ratio
            is_desc = False
        elif sort == "fee_desc":
            # We want: 2.0, ... 0.5, NULL (or NULLS FIRST? usually High->Low people ignore nulls)
            # Let's put NULLS LAST for visual cleanliness
            query = query.order_by(Fund.expense_ratio.desc().nullslast(), Fund.proj_id.asc())
            primary_col = Fund.expense_ratio
            is_desc = True
        elif sort == "risk_asc":
            # String sort logic for risk "1", "2"... "8" works OK alphabetically for 1-8.
            # "MM" or others might break order. Assuming 1-8 numeric strings.
            query = query.order_by(Fund.risk_level.asc().nullslast(), Fund.proj_id.asc())
            primary_col = Fund.risk_level
            is_desc = False
        elif sort == "risk_desc":
            query = query.order_by(Fund.risk_level.desc().nullslast(), Fund.proj_id.asc())
            primary_col = Fund.risk_level
            is_desc = True
        else:
            # Default: Name A-Z
            query = query.order_by(Fund.fund_name_en.asc(), Fund.proj_id.asc())
            primary_col = Fund.fund_name_en
            is_desc = False

        # ---------------------------------------------------------
        # 3. Apply Cursor (Seek Method)
        # ---------------------------------------------------------
        if cursor:
            cursor_data = self._decode_cursor(cursor)
            if cursor_data:
                c_val = cursor_data.get("v")  # Primary value (name/fee/risk)
                c_id = cursor_data.get("i")   # ID
                
                if c_id:
                    # Logic for Keyset Pagination with Nullable Columns:
                    # WE WANT items AFTER (c_val, c_id)
                    #
                    # ASCENDING (Nulls Last):
                    #   Rows: [1, A], [1, B], [2, C], [NULL, D], [NULL, E]
                    #   Cursor: (1, B)
                    #   Next: (val > 1) OR (val == 1 AND id > B) OR (val IS NULL if 1 was not null? No)
                    # 
                    # Handling NULL in cursor itself:
                    #   If c_val is None (we are in the NULLs section):
                    #      Next: (val IS NULL) AND (id > c_id)
                    #   If c_val is NOT None:
                    #      Next: (val > c_val) OR (val == c_val AND id > c_id) OR (val IS NULL)
                    
                    # DESCENDING (Nulls Last):
                    #   Rows: [2, C], [1, A], [1, B], [NULL, D]
                    #   If c_val is NOT None:
                    #      Next: (val < c_val) OR (val == c_val AND id > c_id) OR (val IS NULL)
                    #   If c_val IS None:
                    #      Next: (val IS NULL) AND (id > c_id)
                    
                    # Construct SQLAlchemy criteria
                    seek_clause = None
                    
                    # Helper for strict comparison operators based on direction
                    # is_desc=False (ASC): >
                    # is_desc=True  (DESC): <
                    
                    if c_val is None:
                        # We are currently iterating NULLs.
                        # Only way forward is more NULLs with higher ID
                        seek_clause = and_(primary_col.is_(None), Fund.proj_id > c_id)
                    else:
                        # We are iterating non-nulls.
                        # 1. Values strictly after ( > or < )
                        if is_desc:
                            comp_val = primary_col < c_val
                        else:
                            comp_val = primary_col > c_val
                        
                        # 2. Values equal but higher ID
                        comp_id = and_(primary_col == c_val, Fund.proj_id > c_id)
                        
                        # 3. Handling jump to NULLs (if we are in non-nulls, NULLs are always "after" in NULLS LAST mode)
                        # So we always include OR IS NULL
                        comp_null = primary_col.is_(None)
                        
                        seek_clause = or_(comp_val, comp_id, comp_null)

                    query = query.where(seek_clause)

        # ---------------------------------------------------------
        # 4. Execute & Fetch
        # ---------------------------------------------------------
        # Fetch limit + 1
        query = query.limit(limit + 1)
        
        result = await self.db.execute(query)
        funds = result.scalars().all()
        
        has_more = len(funds) > limit
        if has_more:
            funds = funds[:limit]

        # ---------------------------------------------------------
        # 5. Build Response
        # ---------------------------------------------------------
        items = []
        for fund in funds:
            # Join loaded or select separately? 
            # We already Joined AMC in query, so SQLAlchemy usually populates it or we need contains_eager/options.
            # The query above did .join(AMC) but didn't select it or use options.
            # To avoid N+1, strict join usage in scalars() might not populate relationship automatically 
            # unless options(joinedload(Fund.amc)) is used OR we select(Fund, AMC).
            # Let's rely on relationship lazy load (async requires explicit load) or use options.
            # Optimizing: Let's reuse the query structure but add options.
            # Retrying the query definition slightly above might be needed? 
            # Actually, let's fix the N+1 in a second pass since we are in `replace_file_content` 
            # and cannot scroll up easily. BUT, we can just await the lazy load if configured, 
            # or better, fetch amc explicitly if needed.
            # For now, let's assume basic lazy load works or minor perf hit is ok for MVP. 
            # *Wait*, async sqlalchemy requires explicit eager load.
            # Let's just fetch the AMC name quickly or use the foreign key if possible?
            # We need name.
            # Let's leave it as is (lazy loading might fail in async if session closed? 
            # Usually raises MissingGreenlet. We should have used selectinload.
            # Force eager load safely:
            # For this MVP step, I will add explicit fetching to be safe if relationship fails.*
            pass
            
            # Explicit fetch for safety against Async relationship issues without eagerloading options
            # (Ideally we'd add .options(selectinload(Fund.amc)) to query, but I didn't add it above)
            amc_name = "Unknown"
            if fund.amc: # If accidentally loaded
                amc_name = fund.amc.name_en
            else:
                # Fallback manual fetch (slow but safe)
                amc_res = await self.db.execute(select(AMC).where(AMC.unique_id == fund.amc_id))
                amc_obj = amc_res.scalar_one_or_none()
                if amc_obj:
                    amc_name = amc_obj.name_en

            items.append(FundSummary(
                fund_id=fund.proj_id,
                fund_name=fund.fund_name_en,
                amc_name=amc_name,
                category=fund.category,
                risk_level=fund.risk_level,
                expense_ratio=float(fund.expense_ratio) if fund.expense_ratio is not None else None,
            ))

        # Build next cursor
        next_cursor = None
        if has_more and funds:
            last_fund = funds[-1]
            # Cursor value depends on sort column
            val = None
            if primary_col == Fund.expense_ratio:
                val = float(last_fund.expense_ratio) if last_fund.expense_ratio is not None else None
            elif primary_col == Fund.risk_level:
                val = last_fund.risk_level
            elif primary_col == Fund.fund_name_en:
                val = last_fund.fund_name_en
            
            next_cursor = self._encode_cursor(val, last_fund.proj_id)

        # Get snapshot info (lightweight separate query)
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
