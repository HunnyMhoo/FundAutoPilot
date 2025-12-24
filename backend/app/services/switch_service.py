"""
Switch Impact Preview Service

Calculates deterministic switch impact metrics (fee, risk, category) for fund switching scenarios.
"""

import logging
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fund_orm import Fund
from app.models.fund import (
    SwitchPreviewRequest,
    SwitchPreviewResponse,
    InputsEcho,
    Deltas,
    Explainability,
    Coverage,
)

logger = logging.getLogger(__name__)

# Constants
MIN_AMOUNT_THB = 1000
MAX_AMOUNT_THB = 1000000000
DEFAULT_DISCLAIMERS = [
    "Illustrative estimate for education only. Not financial advice.",
    "Expense ratio may change over time. Check latest factsheet.",
]


class SwitchService:
    """Service for calculating switch impact preview."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_switch_preview(self, request: SwitchPreviewRequest) -> SwitchPreviewResponse:
        """
        Generate switch impact preview for switching from current to target fund.
        
        Args:
            request: SwitchPreviewRequest with current_fund_id, target_fund_id, amount_thb
            
        Returns:
            SwitchPreviewResponse with calculated deltas, explanation, and coverage status
            
        Raises:
            ValueError: If fund not found or invalid request
        """
        # Validate that funds are different
        if request.current_fund_id == request.target_fund_id:
            raise ValueError("Current and target funds must be different")
        
        # Fetch both funds
        current_fund = await self._fetch_fund(request.current_fund_id)
        target_fund = await self._fetch_fund(request.target_fund_id)
        
        # Extract data
        current_expense_ratio = float(current_fund.expense_ratio) if current_fund.expense_ratio is not None else None
        target_expense_ratio = float(target_fund.expense_ratio) if target_fund.expense_ratio is not None else None
        
        # Use risk_level_int if available, fallback to risk_level string
        current_risk = current_fund.risk_level_int if current_fund.risk_level_int is not None else (
            int(current_fund.risk_level) if current_fund.risk_level and current_fund.risk_level.isdigit() else None
        )
        target_risk = target_fund.risk_level_int if target_fund.risk_level_int is not None else (
            int(target_fund.risk_level) if target_fund.risk_level and target_fund.risk_level.isdigit() else None
        )
        
        current_category = current_fund.category
        target_category = target_fund.category
        
        # Calculate deltas
        expense_ratio_delta = None
        annual_fee_thb_delta = None
        if current_expense_ratio is not None and target_expense_ratio is not None:
            expense_ratio_delta = target_expense_ratio - current_expense_ratio
            # Annual fee drag difference = Amount × (Target ER − Current ER)
            annual_fee_thb_delta = round(request.amount_thb * (expense_ratio_delta / 100.0))
        
        risk_level_delta = None
        if current_risk is not None and target_risk is not None:
            risk_level_delta = target_risk - current_risk
        
        category_changed = None
        if current_category is not None and target_category is not None:
            category_changed = current_category != target_category
        
        # Classify coverage
        coverage = self._classify_coverage(
            current_expense_ratio,
            target_expense_ratio,
            current_risk,
            target_risk,
            current_category,
            target_category,
        )
        
        # Generate explanation
        explainability = self._generate_explanation(
            current_fund.fund_name_en,
            target_fund.fund_name_en,
            request.amount_thb,
            expense_ratio_delta,
            annual_fee_thb_delta,
            current_expense_ratio,
            target_expense_ratio,
            current_risk,
            target_risk,
            risk_level_delta,
            current_category,
            target_category,
            category_changed,
            coverage,
        )
        
        # Build inputs echo
        inputs_echo = InputsEcho(
            current_fund_id=request.current_fund_id,
            target_fund_id=request.target_fund_id,
            amount_thb=request.amount_thb,
            current_expense_ratio=current_expense_ratio,
            target_expense_ratio=target_expense_ratio,
            current_risk_level=str(current_risk) if current_risk is not None else None,
            target_risk_level=str(target_risk) if target_risk is not None else None,
            current_category=current_category,
            target_category=target_category,
        )
        
        deltas = Deltas(
            expense_ratio_delta=expense_ratio_delta,
            annual_fee_thb_delta=annual_fee_thb_delta,
            risk_level_delta=risk_level_delta,
            category_changed=category_changed,
        )
        
        return SwitchPreviewResponse(
            inputs_echo=inputs_echo,
            deltas=deltas,
            explainability=explainability,
            coverage=coverage,
        )
    
    async def _fetch_fund(self, fund_id: str) -> Fund:
        """Fetch fund by ID, raising ValueError if not found."""
        # Try lookup by class_abbr_name first (for share classes)
        query = select(Fund).where(Fund.class_abbr_name == fund_id)
        result = await self.db.execute(query)
        fund = result.scalar_one_or_none()
        
        # If not found by class name, try proj_id
        if fund is None:
            query = select(Fund).where(Fund.proj_id == fund_id).where(Fund.class_abbr_name == "")
            result = await self.db.execute(query)
            fund = result.scalar_one_or_none()
        
        if fund is None:
            raise ValueError(f"Fund not found: {fund_id}")
        
        return fund
    
    def _classify_coverage(
        self,
        current_expense_ratio: float | None,
        target_expense_ratio: float | None,
        current_risk: int | None,
        target_risk: int | None,
        current_category: str | None,
        target_category: str | None,
    ) -> Coverage:
        """
        Classify data coverage status.
        
        Rules:
        - BLOCKED: Expense ratio missing for either fund (fee delta is anchor metric)
        - HIGH: All data present (expense ratio, risk, category)
        - MEDIUM: Expense ratio present, but risk or category missing
        - LOW: Expense ratio present, but both risk and category missing
        """
        missing_fields = []
        
        # Check expense ratios (required)
        if current_expense_ratio is None:
            missing_fields.append("current_expense_ratio")
        if target_expense_ratio is None:
            missing_fields.append("target_expense_ratio")
        
        # If expense ratio missing, BLOCKED
        if missing_fields:
            return Coverage(
                status="BLOCKED",
                missing_fields=missing_fields,
                blocking_reason="Expense ratio data is required for fee impact calculation.",
                suggested_next_action="Choose another fund with fee data.",
            )
        
        # Check optional fields
        if current_risk is None:
            missing_fields.append("current_risk_level")
        if target_risk is None:
            missing_fields.append("target_risk_level")
        if current_category is None:
            missing_fields.append("current_category")
        if target_category is None:
            missing_fields.append("target_category")
        
        # Classify based on missing optional fields
        risk_missing = current_risk is None or target_risk is None
        category_missing = current_category is None or target_category is None
        
        if not risk_missing and not category_missing:
            status = "HIGH"
        elif risk_missing and category_missing:
            status = "LOW"
        else:
            status = "MEDIUM"
        
        return Coverage(
            status=status,
            missing_fields=missing_fields,
            blocking_reason=None,
            suggested_next_action=None,
        )
    
    def _generate_explanation(
        self,
        current_fund_name: str,
        target_fund_name: str,
        amount_thb: float,
        expense_ratio_delta: float | None,
        annual_fee_thb_delta: float | None,
        current_expense_ratio: float | None,
        target_expense_ratio: float | None,
        current_risk: int | None,
        target_risk: int | None,
        risk_level_delta: int | None,
        current_category: str | None,
        target_category: str | None,
        category_changed: bool | None,
        coverage: Coverage,
    ) -> Explainability:
        """
        Generate deterministic explanation paragraph.
        
        Template structure:
        1. Fee impact statement (if available)
        2. Risk change statement (if available)
        3. Category change statement (if available)
        4. Disclaimer about illustrative nature
        """
        # Build formula display
        formula_display = "Annual fee difference = Amount × (Target expense ratio − Current expense ratio)"
        
        # Build rationale short (1-2 lines)
        rationale_short_parts = []
        if annual_fee_thb_delta is not None:
            if annual_fee_thb_delta > 0:
                rationale_short_parts.append(f"Increases annual fee drag by approximately {abs(annual_fee_thb_delta):,.0f} THB per year.")
            elif annual_fee_thb_delta < 0:
                rationale_short_parts.append(f"Decreases annual fee drag by approximately {abs(annual_fee_thb_delta):,.0f} THB per year.")
            else:
                rationale_short_parts.append("No change in annual fee drag.")
        else:
            rationale_short_parts.append("Fee impact cannot be calculated due to missing expense ratio data.")
        
        if risk_level_delta is not None:
            if risk_level_delta > 0:
                rationale_short_parts.append(f"Risk level increases from {current_risk} to {target_risk}.")
            elif risk_level_delta < 0:
                rationale_short_parts.append(f"Risk level decreases from {current_risk} to {target_risk}.")
            else:
                rationale_short_parts.append("Risk level remains unchanged.")
        
        rationale_short = " ".join(rationale_short_parts)
        
        # Build rationale paragraph (3-5 sentences)
        paragraph_parts = []
        
        # Fee impact sentence
        if annual_fee_thb_delta is not None:
            amount_formatted = f"{amount_thb:,.0f}"
            current_er_formatted = f"{current_expense_ratio:.2f}%"
            target_er_formatted = f"{target_expense_ratio:.2f}%"
            
            if annual_fee_thb_delta > 0:
                paragraph_parts.append(
                    f"Switching from {current_fund_name} to {target_fund_name} increases expected fee drag by approximately {abs(annual_fee_thb_delta):,.0f} THB per year on an investment of {amount_formatted} THB."
                )
            elif annual_fee_thb_delta < 0:
                paragraph_parts.append(
                    f"Switching from {current_fund_name} to {target_fund_name} decreases expected fee drag by approximately {abs(annual_fee_thb_delta):,.0f} THB per year on an investment of {amount_formatted} THB."
                )
            else:
                paragraph_parts.append(
                    f"Switching from {current_fund_name} to {target_fund_name} results in no change in annual fee drag on an investment of {amount_formatted} THB."
                )
            
            paragraph_parts.append(
                f"This calculation uses expense ratios of {current_er_formatted} (current) and {target_er_formatted} (target)."
            )
        else:
            paragraph_parts.append(
                f"Fee impact cannot be calculated for switching from {current_fund_name} to {target_fund_name} due to missing expense ratio data."
            )
        
        # Risk change sentence
        if risk_level_delta is not None:
            if risk_level_delta > 0:
                paragraph_parts.append(
                    f"Risk level moves from {current_risk} to {target_risk}, indicating higher risk exposure."
                )
            elif risk_level_delta < 0:
                paragraph_parts.append(
                    f"Risk level moves from {current_risk} to {target_risk}, indicating lower risk exposure."
                )
            else:
                paragraph_parts.append(
                    f"Risk level remains at {current_risk}, indicating no change in risk exposure."
                )
        elif current_risk is None or target_risk is None:
            paragraph_parts.append("Risk level information is not available for one or both funds.")
        
        # Category change sentence
        if category_changed is not None:
            if category_changed:
                paragraph_parts.append(
                    f"Category shifts from {current_category} to {target_category}, which may change diversification characteristics."
                )
            else:
                paragraph_parts.append(
                    f"Category remains {current_category}, maintaining similar diversification characteristics."
                )
        elif current_category is None or target_category is None:
            paragraph_parts.append("Category information is not available for one or both funds.")
        
        # Disclaimer sentence
        paragraph_parts.append(
            "This is an illustrative estimate based on disclosed expense ratios and metadata, not a forecast of future performance."
        )
        
        rationale_paragraph = " ".join(paragraph_parts)
        
        # Build assumptions
        assumptions = [
            "Expense ratios remain constant (actual ratios may change over time).",
            "Calculation uses annual expense ratio only (excludes one-time fees).",
            "No market performance or tax implications are considered.",
        ]
        
        return Explainability(
            rationale_short=rationale_short,
            rationale_paragraph=rationale_paragraph,
            formula_display=formula_display,
            assumptions=assumptions,
            disclaimers=DEFAULT_DISCLAIMERS,
        )

