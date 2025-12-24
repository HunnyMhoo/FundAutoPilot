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
    aimc_category: str | None = Field(None, description="AIMC fund classification")
    aimc_category_source: str | None = Field(None, description="Source: 'AIMC_CSV' or 'SEC_API'")
    
    # New fields for Fund Card badges (1.2, 1.3)
    dividend_policy: str | None = Field(None, description="Dividend policy: 'Y' (pays dividends) or 'N' (accumulating)")
    management_style: str | None = Field(None, description="Management style display: 'Passive' or 'Active'")
    
    # Note: expense_ratio removed from FundSummary (not displayed in UI, would require expensive per-fund calculations)
    # For accurate expense ratio, see FundDetail response or /funds/{fund_id}/fees endpoint
    
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
                        "risk_level": "6"
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
    
    # AIMC Classification (Tier 1 enhancement)
    aimc_category: str | None = Field(None, description="AIMC fund classification category")
    aimc_category_source: str | None = Field(None, description="Source of AIMC category: 'AIMC_CSV' or 'SEC_API'")
    
    # Investment Constraints (Tier 2 enhancement)
    min_investment: str | None = Field(None, description="Minimum investment amount with currency")
    min_redemption: str | None = Field(None, description="Minimum redemption amount with currency")
    min_balance: str | None = Field(None, description="Minimum balance to maintain with currency")
    redemption_period: str | None = Field(None, description="Redemption period (e.g., 'Every business day')")
    
    # Fund Policy & Management Style (2.3)
    fund_policy_type: str | None = Field(None, description="Fund policy type (e.g., 'Equity', 'Fixed Income')")
    management_style: str | None = Field(None, description="Management style code (e.g., 'PN' for Passive)")
    management_style_desc: str | None = Field(None, description="Management style description (e.g., 'Passive (Index-tracking)')")
    
    # Distribution Policy (2.5)
    dividend_policy: str | None = Field(None, description="Dividend policy: 'Y' (pays dividends) or 'N' (accumulating)")
    dividend_policy_remark: str | None = Field(None, description="Additional dividend policy remarks")
    
    # Share Class Info (2.1) - proj_id for sibling lookup
    proj_id: str | None = Field(None, description="Project ID for looking up sibling share classes")
    class_abbr_name: str | None = Field(None, description="Current share class abbreviation")
    
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


class ConstraintsDelta(BaseModel):
    """Constraints differences between current and target funds."""
    min_subscription_current: str | None = Field(None, description="Current fund minimum subscription (with currency)")
    min_subscription_target: str | None = Field(None, description="Target fund minimum subscription (with currency)")
    min_subscription_diff: str | None = Field(None, description="Descriptive difference in minimum subscription")
    min_redemption_current: str | None = Field(None, description="Current fund minimum redemption (with currency)")
    min_redemption_target: str | None = Field(None, description="Target fund minimum redemption (with currency)")
    min_redemption_diff: str | None = Field(None, description="Descriptive difference in minimum redemption")
    redemption_period_current: str | None = Field(None, description="Current fund redemption period")
    redemption_period_target: str | None = Field(None, description="Target fund redemption period")
    redemption_period_changed: bool | None = Field(None, description="Whether redemption period changed")
    cut_off_time_changed: bool | None = Field(None, description="Whether cut-off times changed")


class Deltas(BaseModel):
    """Calculated deltas between current and target funds."""
    expense_ratio_delta: float | None = Field(None, description="Difference in expense ratio (target - current)")
    annual_fee_thb_delta: float | None = Field(None, description="Annual fee drag difference in THB (rounded to nearest THB)")
    risk_level_delta: int | None = Field(None, description="Risk level change (target - current, integer)")
    category_changed: bool | None = Field(None, description="Whether category changed")
    constraints_delta: ConstraintsDelta | None = Field(None, description="Constraints differences")


class Explainability(BaseModel):
    """Explainability metadata for demo narration."""
    rationale_short: str = Field(..., description="Short rationale (1-2 lines)")
    rationale_paragraph: str = Field(..., description="Full explanation paragraph (3-5 sentences, demo-ready)")
    formula_display: str = Field(..., description="Exact formula text for display")
    assumptions: list[str] = Field(default_factory=list, description="List of assumptions (short bullets)")
    disclaimers: list[str] = Field(default_factory=list, description="Mandatory disclaimers")


class SwitchPreviewMissingFlags(BaseModel):
    """Per-section missing data flags for switch preview."""
    fee_missing: bool = Field(False, description="Fee data is missing for one or both funds")
    risk_missing: bool = Field(False, description="Risk data is missing for one or both funds")
    category_missing: bool = Field(False, description="Category data is missing for one or both funds")
    constraints_missing: bool = Field(False, description="Constraints data is missing for one or both funds")


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
    missing_flags: SwitchPreviewMissingFlags = Field(..., description="Per-section missing data flags")
    data_snapshot_id: str | None = Field(None, description="Data snapshot ID for freshness tracking")
    as_of_date: str | None = Field(None, description="Data freshness date (ISO format)")


# Share Class models (2.1)
class ShareClassInfo(BaseModel):
    """Share class information for fund detail view."""
    class_abbr_name: str = Field(..., description="Share class abbreviation (e.g., 'SCBNK225E')")
    class_name: str | None = Field(None, description="Share class name in Thai")
    class_description: str | None = Field(None, description="Share class description (decoded)")
    is_current: bool = Field(False, description="Whether this is the currently viewed class")
    dividend_policy: str | None = Field(None, description="Dividend policy for this class: 'Y' or 'N'")


class ShareClassListResponse(BaseModel):
    """Response for share class list endpoint."""
    proj_id: str = Field(..., description="Fund project ID")
    fund_name: str = Field(..., description="Fund name")
    current_class: str = Field(..., description="Currently viewed class abbreviation")
    classes: list[ShareClassInfo] = Field(..., description="List of all share classes for this fund")
    total_classes: int = Field(..., description="Total number of share classes")


# Fee Breakdown models (2.2)
class FeeBreakdownItem(BaseModel):
    """Individual fee item for breakdown display."""
    fee_type: str = Field(..., description="Fee type key (e.g., 'management_fee', 'front_end_fee')")
    fee_type_desc: str = Field(..., description="Fee type description in Thai")
    fee_type_desc_en: str | None = Field(None, description="Fee type description in English")
    rate: str | None = Field(None, description="Maximum/prospectus rate")
    rate_unit: str | None = Field(None, description="Rate unit description")
    actual_value: str | None = Field(None, description="Actual charged value")
    actual_value_unit: str | None = Field(None, description="Actual value unit")


class FeeBreakdownSection(BaseModel):
    """Section of fees (transaction or recurring)."""
    section_key: str = Field(..., description="Section key: 'transaction' or 'recurring'")
    section_label: str = Field(..., description="Section display label")
    fees: list[FeeBreakdownItem] = Field(..., description="List of fees in this section")


class FeeBreakdownResponse(BaseModel):
    """Response for fee breakdown endpoint."""
    fund_id: str = Field(..., description="Fund ID")
    class_abbr_name: str | None = Field(None, description="Share class (if applicable)")
    sections: list[FeeBreakdownSection] = Field(..., description="Fee sections")
    total_expense_ratio: float | None = Field(None, description="Total expense ratio percentage")
    total_expense_ratio_actual: float | None = Field(None, description="Actual total expense ratio")
    last_upd_date: str | None = Field(None, description="Last update date for fee data")
