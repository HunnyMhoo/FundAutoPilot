"""Fund API endpoints."""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.fund import FundListResponse
from app.services.fund_service import FundService

router = APIRouter(prefix="/funds", tags=["funds"])


@router.get("", response_model=FundListResponse)
async def list_funds(
    limit: int = Query(25, ge=1, le=100, description="Items per page"),
    cursor: str | None = Query(None, description="Next page cursor"),
    sort: str = Query("name_asc", description="Sort order"),
    q: str | None = Query(None, description="Search term"),
    amc: list[str] | None = Query(None, description="Filter by AMC IDs"),
    category: list[str] | None = Query(None, description="Filter by Category"),
    risk: list[str] | None = Query(None, description="Filter by Risk Levels"),
    fee_band: list[str] | None = Query(None, description="Filter by Fee Band (low, medium, high)"),
    db: AsyncSession = Depends(get_db),
) -> FundListResponse:
    """List mutual funds with optional filters and sorting."""
    service = FundService(db)
    
    filters = {
        "amc": amc,
        "category": category,
        "risk": risk,
        "fee_band": fee_band,
    }
    
    try:
        return await service.list_funds(
            limit=limit,
            cursor=cursor,
            sort=sort,
            q=q,
            filters=filters
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/count")
async def get_fund_count(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get total count of active funds."""
    service = FundService(db)
    count = await service.get_fund_count()
    return {"count": count}
