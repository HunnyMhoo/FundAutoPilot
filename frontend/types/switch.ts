/**
 * TypeScript types for Switch Impact Preview feature
 */

export interface SwitchPreviewRequest {
    current_fund_id: string;
    target_fund_id: string;
    amount_thb: number;
}

export interface InputsEcho {
    current_fund_id: string;
    target_fund_id: string;
    amount_thb: number;
    current_expense_ratio: number | null;
    target_expense_ratio: number | null;
    current_risk_level: string | null;
    target_risk_level: string | null;
    current_category: string | null;
    target_category: string | null;
}

export interface Deltas {
    expense_ratio_delta: number | null;
    annual_fee_thb_delta: number | null;
    risk_level_delta: number | null;
    category_changed: boolean | null;
}

export interface Explainability {
    rationale_short: string;
    rationale_paragraph: string;
    formula_display: string;
    assumptions: string[];
    disclaimers: string[];
}

export interface Coverage {
    status: 'HIGH' | 'MEDIUM' | 'LOW' | 'BLOCKED';
    missing_fields: string[];
    blocking_reason: string | null;
    suggested_next_action: string | null;
}

export interface SwitchPreviewResponse {
    inputs_echo: InputsEcho;
    deltas: Deltas;
    explainability: Explainability;
    coverage: Coverage;
}

