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
    as_of_date: string | null;
    last_updated_at: string | null;
    data_source: string | null;
    data_version: string | null;
}
