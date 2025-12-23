"""Fund API endpoints."""

from fastapi import APIRouter, Depends, Query, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.fund import (
    FundListResponse, 
    FundDetail,
    CategoryListResponse,
    RiskListResponse,
    AMCListResponse
)
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


@router.get("/categories", response_model=CategoryListResponse)
async def get_categories(
    db: AsyncSession = Depends(get_db),
) -> CategoryListResponse:
    """
    Get distinct categories with fund counts.
    
    Returns dataset-driven category options excluding null values,
    ordered by count descending, then alphabetically.
    """
    try:
        service = FundService(db)
        categories = await service.get_categories_with_counts()
        return CategoryListResponse(items=categories)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch categories: {str(e)}")


@router.get("/risks", response_model=RiskListResponse)
async def get_risks(
    db: AsyncSession = Depends(get_db),
) -> RiskListResponse:
    """
    Get distinct risk levels with fund counts.
    
    Returns dataset-driven risk level options excluding null values,
    ordered by risk level ascending (numeric if applicable).
    """
    try:
        service = FundService(db)
        risks = await service.get_risks_with_counts()
        return RiskListResponse(items=risks)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch risks: {str(e)}")


@router.get("/amcs", response_model=AMCListResponse)
async def get_amcs(
    q: str | None = Query(None, description="Search term for AMC name (typeahead)"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    cursor: str | None = Query(None, description="Pagination cursor for next page"),
    db: AsyncSession = Depends(get_db),
) -> AMCListResponse:
    """
    Get list of AMCs with active fund counts, supporting search and pagination.
    
    Supports typeahead search on AMC names and cursor-based pagination
    for full coverage beyond top 10 AMCs.
    """
    try:
        service = FundService(db)
        result = await service.get_amcs_with_fund_counts(
            search_term=q,
            limit=limit,
            cursor=cursor
        )
        return AMCListResponse(
            items=result["items"],
            next_cursor=result.get("next_cursor")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch AMCs: {str(e)}")


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
