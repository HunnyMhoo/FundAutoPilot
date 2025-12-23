/**
 * API client for fund endpoints
 */

import { FundListResponse } from '@/types/fund';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function fetchFunds(cursor?: string, limit: number = 25): Promise<FundListResponse> {
    const params = new URLSearchParams({
        limit: limit.toString(),
        sort: 'name_asc',
    });

    if (cursor) {
        params.set('cursor', cursor);
    }

    const response = await fetch(`${API_BASE_URL}/funds?${params}`, {
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
