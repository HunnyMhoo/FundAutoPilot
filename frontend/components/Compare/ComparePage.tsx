'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { fetchCompareFunds, CompareFundsResponse } from '@/utils/api/funds';
import { CompareFundColumn } from './CompareFundColumn';
import { ErrorState } from '@/components/FundCatalog/ErrorState';
import styles from './ComparePage.module.css';

interface ComparePageProps {
    idsParam: string;
}

type CompareState = 'loading' | 'loaded' | 'error' | 'invalid';

export function ComparePage({ idsParam }: ComparePageProps) {
    const router = useRouter();
    const [state, setState] = useState<CompareState>('loading');
    const [data, setData] = useState<CompareFundsResponse | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        // Parse IDs from URL
        const ids = idsParam
            .split(',')
            .map(id => id.trim())
            .filter(id => id.length > 0);

        // Validate: must have 2-3 funds
        if (ids.length < 2 || ids.length > 3) {
            setState('invalid');
            setError('Please select 2-3 funds to compare. Redirecting...');
            // Redirect to funds page after a delay
            setTimeout(() => {
                router.push('/funds');
            }, 2000);
            return;
        }

        // Fetch comparison data
        const loadCompareData = async () => {
            setState('loading');
            setError(null);

            try {
                const response = await fetchCompareFunds(ids);
                setData(response);
                setState('loaded');
            } catch (err) {
                const errorMessage = err instanceof Error ? err.message : 'Failed to load comparison data';
                setError(errorMessage);
                setState('error');
            }
        };

        loadCompareData();
    }, [idsParam, router]);

    const handleRetry = () => {
        const ids = idsParam
            .split(',')
            .map(id => id.trim())
            .filter(id => id.length > 0);
        
        fetchCompareFunds(ids)
            .then((response) => {
                setData(response);
                setState('loaded');
                setError(null);
            })
            .catch((err) => {
                const errorMessage = err instanceof Error ? err.message : 'Failed to load comparison data';
                setError(errorMessage);
                setState('error');
            });
    };

    // Invalid state
    if (state === 'invalid') {
        return (
            <div className={styles.container}>
                <div className={styles.header}>
                    <h1 className={styles.title}>Invalid Comparison</h1>
                    <p className={styles.errorMessage}>{error}</p>
                </div>
            </div>
        );
    }

    // Loading state
    if (state === 'loading') {
        return (
            <div className={styles.container}>
                <div className={styles.header}>
                    <h1 className={styles.title}>Compare Funds</h1>
                </div>
                <div className={styles.loadingGrid}>
                    {[1, 2, 3].map((i) => (
                        <div key={i} className={styles.skeletonColumn}></div>
                    ))}
                </div>
            </div>
        );
    }

    // Error state
    if (state === 'error') {
        return (
            <div className={styles.container}>
                <div className={styles.header}>
                    <h1 className={styles.title}>Compare Funds</h1>
                </div>
                <ErrorState message={error || 'Failed to load comparison data'} onRetry={handleRetry} />
            </div>
        );
    }

    // Loaded state
    if (!data || data.funds.length === 0) {
        return (
            <div className={styles.container}>
                <div className={styles.header}>
                    <h1 className={styles.title}>Compare Funds</h1>
                    <p className={styles.errorMessage}>No funds to compare</p>
                </div>
            </div>
        );
    }

    // Show error banner if there are non-fatal errors
    const hasErrors = data.errors && data.errors.length > 0;

    const handleSwitchPreview = () => {
        router.push(`/switch?ids=${idsParam}`);
    };

    return (
        <div className={styles.container}>
            <div className={styles.header}>
                <div className={styles.headerRow}>
                    <h1 className={styles.title}>Compare Funds</h1>
                    <button
                        className={styles.switchButton}
                        onClick={handleSwitchPreview}
                        title="Switch Impact Preview"
                    >
                        Switch Impact Preview
                    </button>
                </div>
                {hasErrors && (
                    <div className={styles.errorBanner}>
                        <strong>Note:</strong> {data.errors.join(' ')}
                    </div>
                )}
            </div>
            <div className={styles.grid}>
                {data.funds.map((fund) => (
                    <CompareFundColumn key={fund.fund_id} fund={fund} />
                ))}
            </div>
        </div>
    );
}

