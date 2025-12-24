/**
 * TypeScript types for Fund API
 */

export interface FundSummary {
    fund_id: string;
    fund_name: string;
    amc_name: string;
    category: string | null;
    risk_level: string | null;
    expense_ratio: number | null;
    aimc_category: string | null;
    aimc_category_source: string | null;
}

export interface FundListResponse {
    items: FundSummary[];
    next_cursor: string | null;
    as_of_date: string;
    data_snapshot_id: string;
}

export type CatalogState =
    | 'idle'
    | 'loading_initial'
    | 'loaded'
    | 'error_initial'
    | 'loading_more'
    | 'error_load_more'
    | 'end_of_results';

export interface FundDetail {
    fund_id: string;
    fund_name: string;
    fund_abbr: string | null;
    category: string | null;
    amc_id: string;
    amc_name: string;
    risk_level: string | null;
    expense_ratio: number | null;
    
    // AIMC Classification (Tier 1 enhancement)
    aimc_category: string | null;
    aimc_category_source: string | null;  // 'AIMC_CSV' or 'SEC_API'
    
    // Investment Constraints (Tier 2 enhancement)
    min_investment: string | null;
    min_redemption: string | null;
    min_balance: string | null;
    redemption_period: string | null;
    
    as_of_date: string | null;
    last_updated_at: string | null;
    data_source: string | null;
    data_version: string | null;
}

// Compare types for US-N6
export interface FeeRow {
    fee_type_desc: string;
    rate: string | null;
    rate_unit: string | null;
    actual_value: string | null;
    actual_value_unit: string | null;
    fee_other_desc: string | null;
    last_upd_date: string | null;
    class_abbr_name: string | null;
}

export interface FeeGroup {
    category: string;
    display_label: string;
    fees: FeeRow[];
}

export interface DealingConstraints {
    redemp_period: string | null;
    redemp_period_oth: string | null;
    settlement_period: string | null;
    buying_cut_off_time: string | null;
    selling_cut_off_time: string | null;
    minimum_sub_ipo: string | null;
    minimum_sub_ipo_cur: string | null;
    minimum_sub: string | null;
    minimum_sub_cur: string | null;
    minimum_redempt: string | null;
    minimum_redempt_cur: string | null;
    minimum_redempt_unit: string | null;
    lowbal_val: number | null;
    lowbal_val_cur: string | null;
    lowbal_unit: number | null;
    last_upd_date_redemption: string | null;
    last_upd_date_investment: string | null;
    class_shown: string | null;
}

export interface DividendDetail {
    book_closing_date: string | null;
    payment_date: string | null;
    dividend_per_share: string | null;
}

export interface DistributionData {
    dividend_policy: string | null;
    dividend_policy_remark: string | null;
    recent_dividends: DividendDetail[];
    last_upd_date: string | null;
    class_shown: string | null;
}

export interface MissingFlags {
    fees_missing: boolean;
    risk_missing: boolean;
    dealing_missing: boolean;
    distribution_missing: boolean;
}

export interface FundIdentity {
    fund_id: string;
    fund_name: string;
    fund_abbr: string | null;
    amc_id: string;
    amc_name: string;
    category: string | null;
}

export interface RiskData {
    risk_level: string | null;
    risk_level_desc: string | null;
    last_upd_date: string | null;
}

export interface CompareFundData {
    fund_id: string;
    identity: FundIdentity;
    risk: RiskData | null;
    fees: FeeGroup[];
    dealing_constraints: DealingConstraints | null;
    distribution: DistributionData | null;
    missing_flags: MissingFlags;
    data_freshness: Record<string, string | null>;
}

export interface CompareFundsResponse {
    funds: CompareFundData[];
    errors: string[];
}
