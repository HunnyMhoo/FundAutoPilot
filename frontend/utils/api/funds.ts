/**
 * API client for fund endpoints
 */

import { FundListResponse, FundDetail } from '@/types/fund';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Define these types here or import if moved to @/types/fund
export interface FundFilters {
    amc: string[];
    category: string[];
    risk: string[];
    fee_band: string[];
}

export type SortOption =
    | 'name_asc'
    | 'name_desc'
    | 'fee_asc'
    | 'fee_desc'
    | 'risk_asc'
    | 'risk_desc';

export async function fetchFunds(
    cursor?: string | null, // Allow null explicit
    limit: number = 25,
    q?: string,
    filters?: Partial<FundFilters>,
    sort: SortOption = 'name_asc'
): Promise<FundListResponse> {
    const params = new URLSearchParams();

    // Basic params
    params.set('limit', limit.toString());
    params.set('sort', sort);
    if (cursor) params.set('cursor', cursor);
    if (q) params.set('q', q);

    // Filter array serialization
    // FastAPI expects repeated keys: amc=A&amc=B
    if (filters) {
        if (filters.amc?.length) filters.amc.forEach(v => params.append('amc', v));
        if (filters.category?.length) filters.category.forEach(v => params.append('category', v));
        if (filters.risk?.length) filters.risk.forEach(v => params.append('risk', v));
        if (filters.fee_band?.length) filters.fee_band.forEach(v => params.append('fee_band', v));
    }

    const response = await fetch(`${API_BASE_URL}/funds?${params.toString()}`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
        },
    });

    if (!response.ok) {
        throw new Error(`Failed to fetch funds: ${response.status} ${response.statusText}`);
    }

    return response.json();
}

export async function fetchFundCount(): Promise<number> {
    const response = await fetch(`${API_BASE_URL}/funds/count`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
        },
    });

    if (!response.ok) {
        throw new Error(`Failed to fetch fund count: ${response.status}`);
    }

    const data = await response.json();
    return data.count;
}

export async function fetchFundDetail(fundId: string): Promise<FundDetail> {
    const response = await fetch(`${API_BASE_URL}/funds/${encodeURIComponent(fundId)}`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
        },
    });

    if (!response.ok) {
        if (response.status === 404) {
            throw new Error(`Fund not found: ${fundId}`);
        }
        if (response.status === 400) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `Invalid fund ID: ${fundId}`);
        }
        throw new Error(`Failed to fetch fund details: ${response.status} ${response.statusText}`);
    }

    return response.json();
}
