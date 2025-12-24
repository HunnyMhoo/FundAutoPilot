/**
 * API client for switch impact preview endpoints
 */

import { SwitchPreviewRequest, SwitchPreviewResponse } from '@/types/switch';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function fetchSwitchPreview(
    request: SwitchPreviewRequest
): Promise<SwitchPreviewResponse> {
    const response = await fetch(`${API_BASE_URL}/switch/preview`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
    });

    if (!response.ok) {
        if (response.status === 400) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || 'Invalid request for switch preview');
        }
        if (response.status === 404) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || 'Fund not found');
        }
        if (response.status === 422) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || 'Validation error: Please check your inputs');
        }
        throw new Error(`Failed to fetch switch preview: ${response.status} ${response.statusText}`);
    }

    return response.json();
}

