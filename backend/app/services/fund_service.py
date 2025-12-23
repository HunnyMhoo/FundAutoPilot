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
        sort: str = "name_asc"
    ) -> FundListResponse:
        """
        List funds with cursor-based pagination.
        
        Args:
            limit: Number of items to return (max 100)
            cursor: Base64-encoded cursor for pagination
            sort: Sort order (currently only 'name_asc' supported)
        
        Returns:
            FundListResponse with items, next_cursor, and metadata
        """
        # Clamp limit
        limit = min(max(1, limit), 100)
        
        # Build base query - only active (RG) funds
        query = (
            select(Fund)
            .join(AMC, Fund.amc_id == AMC.unique_id)
            .where(Fund.fund_status == "RG")
            .order_by(Fund.fund_name_en, Fund.proj_id)
        )
        
        # Apply cursor if provided
        if cursor:
            cursor_data = self._decode_cursor(cursor)
            if cursor_data:
                # Keyset pagination: get items after this (name, id) pair
                query = query.where(
                    or_(
                        Fund.fund_name_en > cursor_data.n,
                        and_(
                            Fund.fund_name_en == cursor_data.n,
                            Fund.proj_id > cursor_data.i
                        )
                    )
                )
        
        # Fetch limit + 1 to determine if there's a next page
        query = query.limit(limit + 1)
        
        result = await self.db.execute(query)
        funds = result.scalars().all()
        
        # Check if there are more results
        has_more = len(funds) > limit
        if has_more:
            funds = funds[:limit]  # Remove the extra item
        
        # Build response items with AMC names
        items = []
        for fund in funds:
            # Fetch AMC for each fund (could optimize with joined load)
            amc_result = await self.db.execute(
                select(AMC).where(AMC.unique_id == fund.amc_id)
            )
            amc = amc_result.scalar_one_or_none()
            
            items.append(FundSummary(
                fund_id=fund.proj_id,
                fund_name=fund.fund_name_en,
                amc_name=amc.name_en if amc else "Unknown",
                category=fund.category,
                risk_level=fund.risk_level,
                expense_ratio=float(fund.expense_ratio) if fund.expense_ratio else None,
            ))
        
        # Build next cursor
        next_cursor = None
        if has_more and funds:
            last_fund = funds[-1]
            next_cursor = self._encode_cursor(last_fund.fund_name_en, last_fund.proj_id)
        
        # Get latest snapshot info
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
    
    def _encode_cursor(self, name: str, fund_id: str) -> str:
        """Encode cursor data to base64 string."""
        data = {"n": name, "i": fund_id}
        json_str = json.dumps(data, ensure_ascii=False)
        return base64.urlsafe_b64encode(json_str.encode()).decode()
    
    def _decode_cursor(self, cursor: str) -> CursorData | None:
        """Decode cursor from base64 string."""
        try:
            json_str = base64.urlsafe_b64decode(cursor.encode()).decode()
            data = json.loads(json_str)
            return CursorData(n=data["n"], i=data["i"])
        except Exception:
            return None
