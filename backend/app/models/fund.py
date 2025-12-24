"""Pydantic schemas for Fund API requests and responses."""

from datetime import datetime
from pydantic import BaseModel, Field


class FundSummary(BaseModel):
    """Summary of a fund for catalog listing."""
    
    fund_id: str = Field(..., description="Unique fund identifier (proj_id)")
    fund_name: str = Field(..., description="Fund name in English")
    amc_name: str = Field(..., description="Asset Management Company name")
    category: str | None = Field(None, description="Fund category/type")
    risk_level: str | None = Field(None, description="Risk level (1-8 or descriptive)")
    expense_ratio: float | None = Field(None, description="Annual expense ratio percentage")
    
    class Config:
        from_attributes = True


class FundListResponse(BaseModel):
    """Response for paginated fund list."""
    
    items: list[FundSummary] = Field(..., description="List of funds")
    next_cursor: str | None = Field(
        None, 
        description="Cursor for next page, null if end of results"
    )
    as_of_date: str = Field(..., description="Data freshness date (ISO format)")
    data_snapshot_id: str = Field(..., description="Unique identifier for this data snapshot")
    
    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "fund_id": "M0008_2537",
                        "fund_name": "THE RUANG KHAO 4 FUND",
                        "amc_name": "KASIKORN ASSET MANAGEMENT",
                        "category": "Equity",
                        "risk_level": "6",
                        "expense_ratio": 2.01
                    }
                ],
                "next_cursor": "eyJuIjoiVEhFIFJVQU5HIiwiaSI6Ik0wMDA4XzI1MzcifQ==",
                "as_of_date": "2024-12-23",
                "data_snapshot_id": "20241223070000"
            }
        }


class CursorData(BaseModel):
    """Internal cursor structure for keyset pagination."""
    
    n: str = Field(..., description="Last fund name")
    i: str = Field(..., description="Last fund ID")


class FundDetail(BaseModel):
    """Detailed fund information for detail view."""
    
    fund_id: str = Field(..., description="Unique fund identifier (proj_id)")
    fund_name: str = Field(..., description="Fund name in English")
    fund_abbr: str | None = Field(None, description="Fund abbreviation")
    category: str | None = Field(None, description="Fund category/type")
    amc_id: str = Field(..., description="Asset Management Company ID")
    amc_name: str = Field(..., description="Asset Management Company name")
    risk_level: str | None = Field(None, description="Risk level (1-8 or descriptive)")
    expense_ratio: float | None = Field(None, description="Annual expense ratio percentage (rounded to 3 decimals)")
    as_of_date: str | None = Field(None, description="Data snapshot date (ISO format)")
    last_updated_at: str | None = Field(None, description="Last update timestamp (ISO format)")
    data_source: str | None = Field(None, description="Data source identifier")
    data_version: str | None = Field(None, description="Data version identifier")
    
    class Config:
        from_attributes = True


# Filter metadata models for US-N3
class CategoryItem(BaseModel):
    """Category filter option with count."""
    value: str = Field(..., description="Category name")
    count: int = Field(..., description="Number of funds in this category")


class RiskItem(BaseModel):
    """Risk level filter option with count."""
    value: str = Field(..., description="Risk level (1-8 or descriptive)")
    count: int = Field(..., description="Number of funds with this risk level")


class AMCItem(BaseModel):
    """AMC filter option with count."""
    id: str = Field(..., description="AMC unique identifier")
    name: str = Field(..., description="AMC name")
    count: int = Field(..., description="Number of funds from this AMC")


class CategoryListResponse(BaseModel):
    """Response for category filter metadata."""
    items: list[CategoryItem] = Field(..., description="List of categories with counts")


class RiskListResponse(BaseModel):
    """Response for risk level filter metadata."""
    items: list[RiskItem] = Field(..., description="List of risk levels with counts")


class AMCListResponse(BaseModel):
    """Response for AMC filter metadata with pagination."""
    items: list[AMCItem] = Field(..., description="List of AMCs with counts")
    next_cursor: str | None = Field(
        None,
        description="Cursor for next page, null if end of results"
    )


class MetaResponse(BaseModel):
    """Response for home page metadata (fund count and freshness)."""
    total_fund_count: int = Field(..., description="Total number of active funds")
    data_as_of: str = Field(..., description="Data freshness date (ISO format YYYY-MM-DD)")
    data_source: str | None = Field(None, description="Data source identifier")


# Compare models for US-N6
class FeeRow(BaseModel):
    """Individual fee row from SEC API."""
    fee_type_desc: str = Field(..., description="Fee type description")
    rate: str | None = Field(None, description="Published/prospectus rate")
    rate_unit: str | None = Field(None, description="Unit for rate")
    actual_value: str | None = Field(None, description="Actual value paid")
    actual_value_unit: str | None = Field(None, description="Unit for actual value")
    fee_other_desc: str | None = Field(None, description="Additional notes")
    last_upd_date: str | None = Field(None, description="Last update date")
    class_abbr_name: str | None = Field(None, description="Class abbreviation (if class fund)")


class FeeGroup(BaseModel):
    """Grouped fees by category."""
    category: str = Field(..., description="Category: front_end, back_end, switching, ongoing, other")
    display_label: str = Field(..., description="Human-readable label for category")
    fees: list[FeeRow] = Field(..., description="List of fee rows in this category")


class DealingConstraints(BaseModel):
    """Dealing constraints and liquidity information."""
    # From /redemption endpoint
    redemp_period: str | None = Field(None, description="Redemption period code (1-9, E, T)")
    redemp_period_oth: str | None = Field(None, description="Redemption period description (if code=9)")
    settlement_period: str | None = Field(None, description="Settlement period")
    buying_cut_off_time: str | None = Field(None, description="Cut-off time for buying")
    selling_cut_off_time: str | None = Field(None, description="Cut-off time for selling")
    
    # From /investment endpoint
    minimum_sub_ipo: str | None = Field(None, description="Minimum subscription (IPO)")
    minimum_sub_ipo_cur: str | None = Field(None, description="Currency for minimum subscription (IPO)")
    minimum_sub: str | None = Field(None, description="Minimum subscription (subsequent)")
    minimum_sub_cur: str | None = Field(None, description="Currency for minimum subscription")
    minimum_redempt: str | None = Field(None, description="Minimum redemption value")
    minimum_redempt_cur: str | None = Field(None, description="Currency for minimum redemption")
    minimum_redempt_unit: str | None = Field(None, description="Minimum redemption units")
    lowbal_val: float | None = Field(None, description="Low balance value")
    lowbal_val_cur: str | None = Field(None, description="Currency for low balance")
    lowbal_unit: float | None = Field(None, description="Low balance units")
    
    # Metadata
    last_upd_date_redemption: str | None = Field(None, description="Last update date for redemption data")
    last_upd_date_investment: str | None = Field(None, description="Last update date for investment data")
    class_shown: str | None = Field(None, description="Which class was selected")


class DividendDetail(BaseModel):
    """Individual dividend payment detail."""
    book_closing_date: str | None = Field(None, description="Book closing date")
    payment_date: str | None = Field(None, description="Payment date")
    dividend_per_share: str | None = Field(None, description="Dividend per share")


class DistributionData(BaseModel):
    """Distribution/dividend information."""
    dividend_policy: str | None = Field(None, description="Dividend policy")
    dividend_policy_remark: str | None = Field(None, description="Dividend policy remarks")
    recent_dividends: list[DividendDetail] = Field(default_factory=list, description="Recent dividend payments")
    last_upd_date: str | None = Field(None, description="Last update date")
    class_shown: str | None = Field(None, description="Which class was selected")


class MissingFlags(BaseModel):
    """Flags indicating missing data sections."""
    fees_missing: bool = Field(False, description="Fee data is missing")
    risk_missing: bool = Field(False, description="Risk data is missing")
    dealing_missing: bool = Field(False, description="Dealing constraints data is missing")
    distribution_missing: bool = Field(False, description="Distribution data is missing")


class FundIdentity(BaseModel):
    """Fund identity information."""
    fund_id: str = Field(..., description="Fund ID (proj_id)")
    fund_name: str = Field(..., description="Fund name")
    fund_abbr: str | None = Field(None, description="Fund abbreviation")
    amc_id: str = Field(..., description="AMC ID")
    amc_name: str = Field(..., description="AMC name")
    category: str | None = Field(None, description="Category/policy")


class RiskData(BaseModel):
    """Risk and suitability information."""
    risk_level: str | None = Field(None, description="Risk level (1-8 or descriptive)")
    risk_level_desc: str | None = Field(None, description="Risk description")
    last_upd_date: str | None = Field(None, description="Last update date")


class CompareFundData(BaseModel):
    """Comparison data for a single fund."""
    fund_id: str = Field(..., description="Fund ID")
    identity: FundIdentity = Field(..., description="Fund identity information")
    risk: RiskData | None = Field(None, description="Risk data")
    fees: list[FeeGroup] = Field(default_factory=list, description="Grouped fee data")
    dealing_constraints: DealingConstraints | None = Field(None, description="Dealing constraints")
    distribution: DistributionData | None = Field(None, description="Distribution data")
    missing_flags: MissingFlags = Field(default_factory=MissingFlags, description="Missing data flags")
    data_freshness: dict[str, str | None] = Field(default_factory=dict, description="Last update dates per section")


class CompareFundsResponse(BaseModel):
    """Response for fund comparison."""
    funds: list[CompareFundData] = Field(..., description="List of fund comparison data (ordered as requested)")
    errors: list[str] = Field(default_factory=list, description="Non-fatal errors encountered during fetch")


# Switch Impact Preview models for US-N7
class SwitchPreviewRequest(BaseModel):
    """Request for switch impact preview."""
    current_fund_id: str = Field(..., description="Current fund ID (proj_id)")
    target_fund_id: str = Field(..., description="Target fund ID (proj_id)")
    amount_thb: float = Field(..., ge=1000, le=1000000000, description="Investment amount in THB (min: 1,000, max: 1,000,000,000)")


class InputsEcho(BaseModel):
    """Echo of inputs used in calculation."""
    current_fund_id: str = Field(..., description="Current fund ID")
    target_fund_id: str = Field(..., description="Target fund ID")
    amount_thb: float = Field(..., description="Amount in THB")
    current_expense_ratio: float | None = Field(None, description="Current fund expense ratio")
    target_expense_ratio: float | None = Field(None, description="Target fund expense ratio")
    current_risk_level: str | None = Field(None, description="Current fund risk level")
    target_risk_level: str | None = Field(None, description="Target fund risk level")
    current_category: str | None = Field(None, description="Current fund category")
    target_category: str | None = Field(None, description="Target fund category")


class Deltas(BaseModel):
    """Calculated deltas between current and target funds."""
    expense_ratio_delta: float | None = Field(None, description="Difference in expense ratio (target - current)")
    annual_fee_thb_delta: float | None = Field(None, description="Annual fee drag difference in THB (rounded to nearest THB)")
    risk_level_delta: int | None = Field(None, description="Risk level change (target - current, integer)")
    category_changed: bool | None = Field(None, description="Whether category changed")


class Explainability(BaseModel):
    """Explainability metadata for demo narration."""
    rationale_short: str = Field(..., description="Short rationale (1-2 lines)")
    rationale_paragraph: str = Field(..., description="Full explanation paragraph (3-5 sentences, demo-ready)")
    formula_display: str = Field(..., description="Exact formula text for display")
    assumptions: list[str] = Field(default_factory=list, description="List of assumptions (short bullets)")
    disclaimers: list[str] = Field(default_factory=list, description="Mandatory disclaimers")


class Coverage(BaseModel):
    """Data coverage status and missing field information."""
    status: str = Field(..., description="Coverage status: HIGH, MEDIUM, LOW, or BLOCKED")
    missing_fields: list[str] = Field(default_factory=list, description="List of missing field names")
    blocking_reason: str | None = Field(None, description="Reason for blocking if status is BLOCKED")
    suggested_next_action: str | None = Field(None, description="Suggested action for user")


class SwitchPreviewResponse(BaseModel):
    """Response for switch impact preview."""
    inputs_echo: InputsEcho = Field(..., description="Echo of inputs used")
    deltas: Deltas = Field(..., description="Calculated deltas")
    explainability: Explainability = Field(..., description="Explanation and disclaimers")
    coverage: Coverage = Field(..., description="Data coverage status")
