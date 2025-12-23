"""Fund API endpoints."""

from fastapi import APIRouter, Depends, Query, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.fund import FundListResponse, FundDetail
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


@router.get("/amcs")
async def get_amcs(
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Get list of AMCs with active fund counts."""
    service = FundService(db)
    amcs = await service.get_amcs_with_fund_counts()
    return amcs


@router.get("/{fund_id}", response_model=FundDetail)
async def get_fund_by_id(
    fund_id: str = Path(..., description="Unique fund identifier (proj_id)"),
    db: AsyncSession = Depends(get_db),
) -> FundDetail:
    """
    Get detailed fund information by fund_id.
    
    Returns:
        FundDetail with fund information, key facts, and metadata
        
    Raises:
        400: Invalid fund_id format
        404: Fund not found
        500: Server error
    """
    service = FundService(db)
    
    try:
        # Validate fund_id shape (basic validation - fail fast)
        if not fund_id or not fund_id.strip():
            raise HTTPException(
                status_code=400,
                detail="Invalid fund_id: cannot be empty"
            )
        
        fund = await service.get_fund_by_id(fund_id.strip())
        return fund
        
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=404,
                detail=f"Fund not found: {fund_id}"
            )
        else:
            # Invalid ID shape
            raise HTTPException(
                status_code=400,
                detail=error_msg
            )
    except Exception as e:
        # Log the error for debugging but return safe error message
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Unexpected error fetching fund {fund_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while fetching fund details"
        )
