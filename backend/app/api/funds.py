"""Fund API endpoints."""

from fastapi import APIRouter, Depends, Query, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.fund import (
    FundListResponse, 
    FundDetail,
    CategoryListResponse,
    RiskListResponse,
    AMCListResponse,
    MetaResponse,
    CompareFundsResponse,
    ShareClassListResponse,
    FeeBreakdownResponse,
)
from app.services.fund_service import FundService
from app.services.compare_service import CompareService

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
    # #region agent log
    import json; log_data = {"location": "funds.py:36", "message": "list_funds entry", "data": {"limit": limit, "sort": sort, "has_db": db is not None}, "timestamp": __import__("time").time(), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "A"}; open("/Users/test/AutoInvest/FundAutoPilot/.cursor/debug.log", "a").write(json.dumps(log_data) + "\n")
    # #endregion
    service = FundService(db)
    
    filters = {
        "amc": amc,
        "category": category,
        "risk": risk,
        "fee_band": fee_band,
    }
    
    try:
        # #region agent log
        log_data = {"location": "funds.py:47", "message": "Before service.list_funds call", "data": {"filters": filters}, "timestamp": __import__("time").time(), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "C"}; open("/Users/test/AutoInvest/FundAutoPilot/.cursor/debug.log", "a").write(json.dumps(log_data) + "\n")
        # #endregion
        result = await service.list_funds(
            limit=limit,
            cursor=cursor,
            sort=sort,
            q=q,
            filters=filters
        )
        # #region agent log
        log_data = {"location": "funds.py:54", "message": "After service.list_funds call", "data": {"result_items_count": len(result.items) if hasattr(result, "items") else 0}, "timestamp": __import__("time").time(), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "C"}; open("/Users/test/AutoInvest/FundAutoPilot/.cursor/debug.log", "a").write(json.dumps(log_data) + "\n")
        # #endregion
        return result
    except Exception as e:
        # #region agent log
        log_data = {"location": "funds.py:55", "message": "Exception in list_funds", "data": {"error_type": type(e).__name__, "error_msg": str(e)}, "timestamp": __import__("time").time(), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "C"}; open("/Users/test/AutoInvest/FundAutoPilot/.cursor/debug.log", "a").write(json.dumps(log_data) + "\n")
        # #endregion
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/count")
async def get_fund_count(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get total count of active funds."""
    service = FundService(db)
    count = await service.get_fund_count()
    return {"count": count}


@router.get("/meta", response_model=MetaResponse)
async def get_meta(
    db: AsyncSession = Depends(get_db),
) -> MetaResponse:
    """
    Get metadata for home page (fund count and data freshness).
    
    Returns cached metadata with 5-minute TTL to ensure fast response times.
    """
    # #region agent log
    import json; log_data = {"location": "funds.py:68", "message": "get_meta entry", "data": {"has_db": db is not None}, "timestamp": __import__("time").time(), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "B"}; open("/Users/test/AutoInvest/FundAutoPilot/.cursor/debug.log", "a").write(json.dumps(log_data) + "\n")
    # #endregion
    try:
        service = FundService(db)
        # #region agent log
        log_data = {"location": "funds.py:79", "message": "Before service.get_meta_stats call", "data": {}, "timestamp": __import__("time").time(), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "B"}; open("/Users/test/AutoInvest/FundAutoPilot/.cursor/debug.log", "a").write(json.dumps(log_data) + "\n")
        # #endregion
        stats = await service.get_meta_stats()
        # #region agent log
        log_data = {"location": "funds.py:80", "message": "After service.get_meta_stats call", "data": {"stats_keys": list(stats.keys()) if isinstance(stats, dict) else "not_dict"}, "timestamp": __import__("time").time(), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "B"}; open("/Users/test/AutoInvest/FundAutoPilot/.cursor/debug.log", "a").write(json.dumps(log_data) + "\n")
        # #endregion
        return MetaResponse(**stats)
    except Exception as e:
        # #region agent log
        log_data = {"location": "funds.py:82", "message": "Exception in get_meta", "data": {"error_type": type(e).__name__, "error_msg": str(e)}, "timestamp": __import__("time").time(), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "B"}; open("/Users/test/AutoInvest/FundAutoPilot/.cursor/debug.log", "a").write(json.dumps(log_data) + "\n")
        # #endregion
        raise HTTPException(status_code=500, detail=f"Failed to fetch metadata: {str(e)}")


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


@router.get("/compare", response_model=CompareFundsResponse)
async def compare_funds(
    ids: str = Query(..., description="Comma-separated fund IDs (2-3 funds)"),
    db: AsyncSession = Depends(get_db),
) -> CompareFundsResponse:
    """
    Compare 2-3 funds side-by-side.
    
    Returns comparison data including identity, risk, fees, dealing constraints,
    and distribution information for each fund.
    
    Args:
        ids: Comma-separated list of fund IDs (proj_id), must be 2-3 funds
        
    Returns:
        CompareFundsResponse with comparison data for each fund
        
    Raises:
        400: Invalid number of funds (< 2 or > 3), or invalid ID format
        404: One or more fund IDs not found
        500: Server error
    """
    service = CompareService(db)
    
    try:
        # Parse and validate IDs
        fund_ids = [id.strip() for id in ids.split(",") if id.strip()]
        
        if len(fund_ids) < 2:
            raise HTTPException(
                status_code=400,
                detail="At least 2 funds required for comparison"
            )
        
        if len(fund_ids) > 3:
            raise HTTPException(
                status_code=400,
                detail="Maximum 3 funds allowed for comparison"
            )
        
        # Remove duplicates while preserving order
        seen = set()
        unique_ids = []
        for fund_id in fund_ids:
            if fund_id not in seen:
                seen.add(fund_id)
                unique_ids.append(fund_id)
        
        if len(unique_ids) < 2:
            raise HTTPException(
                status_code=400,
                detail="At least 2 distinct funds required for comparison"
            )
        
        return await service.compare_funds(unique_ids)
        
    except HTTPException:
        raise
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=404,
                detail=error_msg
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=error_msg
            )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Unexpected error comparing funds: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while comparing funds"
        )


@router.get("/{fund_id}/share-classes", response_model=ShareClassListResponse)
async def get_share_classes(
    fund_id: str = Path(..., description="Fund identifier (class_abbr_name or proj_id)"),
    db: AsyncSession = Depends(get_db),
) -> ShareClassListResponse:
    """
    Get all share classes for a fund.
    
    Returns list of share classes with descriptions and dividend policies.
    Used for share class navigation on fund detail page (2.1).
    
    Args:
        fund_id: Fund identifier (class_abbr_name or proj_id)
        
    Returns:
        ShareClassListResponse with all share classes for this fund
        
    Raises:
        404: Fund not found
        500: Server error
    """
    service = FundService(db)
    
    try:
        result = await service.get_share_classes(fund_id.strip())
        return ShareClassListResponse(**result)
        
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=404,
                detail=f"Fund not found: {fund_id}"
            )
        else:
            raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Unexpected error fetching share classes for {fund_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while fetching share classes"
        )


@router.get("/{fund_id}/fees", response_model=FeeBreakdownResponse)
async def get_fee_breakdown(
    fund_id: str = Path(..., description="Fund identifier (class_abbr_name or proj_id)"),
    db: AsyncSession = Depends(get_db),
) -> FeeBreakdownResponse:
    """
    Get detailed fee breakdown for a fund.
    
    Returns fees organized by section (transaction fees, recurring fees)
    with both prospectus rates and actual charged values.
    Used for fee breakdown display on fund detail page (2.2).
    
    Args:
        fund_id: Fund identifier (class_abbr_name or proj_id)
        
    Returns:
        FeeBreakdownResponse with categorized fee information
        
    Raises:
        404: Fund not found
        500: Server error
    """
    service = FundService(db)
    
    try:
        result = await service.get_fee_breakdown(fund_id.strip())
        return FeeBreakdownResponse(**result)
        
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=404,
                detail=f"Fund not found: {fund_id}"
            )
        else:
            raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Unexpected error fetching fees for {fund_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while fetching fee breakdown"
        )


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
