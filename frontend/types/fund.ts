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
