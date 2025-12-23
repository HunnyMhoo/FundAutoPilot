"""Fund API endpoints."""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.fund import FundListResponse
from app.services.fund_service import FundService

router = APIRouter(prefix="/funds", tags=["funds"])


@router.get("", response_model=FundListResponse)
async def list_funds(
    limit: int = Query(
        default=25,
        ge=1,
        le=100,
        description="Number of items to return per page"
    ),
    cursor: str | None = Query(
        default=None,
        description="Pagination cursor from previous response"
    ),
    sort: str = Query(
        default="name_asc",
        description="Sort order (currently only 'name_asc' supported)"
    ),
    db: AsyncSession = Depends(get_db),
) -> FundListResponse:
    """
    List mutual funds with cursor-based pagination.
    
    Returns a paginated list of active mutual funds across all AMCs.
    
    - **limit**: Number of items per page (1-100, default 25)
    - **cursor**: Pagination cursor from `next_cursor` in previous response
    - **sort**: Sort order (default: name_asc - alphabetical A-Z)
    
    The response includes:
    - **items**: List of fund summaries
    - **next_cursor**: Cursor for next page (null if end of results)
    - **as_of_date**: Data freshness date
    - **data_snapshot_id**: Unique identifier for this data snapshot
    """
    service = FundService(db)
    
    try:
        return await service.list_funds(limit=limit, cursor=cursor, sort=sort)
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
