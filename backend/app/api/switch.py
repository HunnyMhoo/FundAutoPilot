"""Switch Impact Preview API endpoints."""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.fund import SwitchPreviewRequest, SwitchPreviewResponse
from app.services.switch_service import SwitchService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/switch", tags=["switch"])


@router.post("/preview", response_model=SwitchPreviewResponse)
async def get_switch_preview(
    request: SwitchPreviewRequest,
    db: AsyncSession = Depends(get_db),
) -> SwitchPreviewResponse:
    """
    Generate switch impact preview for switching from current to target fund.
    
    Calculates deterministic metrics:
    - Annual fee drag difference (Amount × (Target ER − Current ER))
    - Risk level change (integer delta)
    - Category change (boolean)
    
    Returns explainable results with coverage status and disclaimers.
    
    Args:
        request: SwitchPreviewRequest with current_fund_id, target_fund_id, amount_thb
        
    Returns:
        SwitchPreviewResponse with calculated deltas, explanation, and coverage status
        
    Raises:
        400: Invalid request (same funds, invalid amount, etc.)
        404: Fund not found
        500: Server error
    """
    service = SwitchService(db)
    
    try:
        return await service.get_switch_preview(request)
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
        logger.error(f"Unexpected error generating switch preview: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while generating switch preview"
        )

