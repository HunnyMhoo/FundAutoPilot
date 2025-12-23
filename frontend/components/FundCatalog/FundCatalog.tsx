'use client';

import { useState, useCallback, useRef } from 'react';
import { FundSummary, CatalogState } from '@/types/fund';
import { fetchFunds } from '@/utils/api/funds';
import { FundCard } from './FundCard';
import { SkeletonLoader } from './SkeletonLoader';
import { LoadMoreButton } from './LoadMoreButton';
import { ErrorState } from './ErrorState';
import { EmptyState } from './EmptyState';
import styles from './FundCatalog.module.css';

interface FundCatalogProps {
    initialAsOfDate?: string;
}

export function FundCatalog({ initialAsOfDate }: FundCatalogProps) {
    const [funds, setFunds] = useState<FundSummary[]>([]);
    const [state, setState] = useState<CatalogState>('idle');
    const [nextCursor, setNextCursor] = useState<string | null>(null);
    const [asOfDate, setAsOfDate] = useState<string>(initialAsOfDate || '');
    const [error, setError] = useState<string | null>(null);

    // Track seen fund IDs for de-duplication
    const seenIds = useRef(new Set<string>());

    // Prevent concurrent requests
    const isLoadingRef = useRef(false);

    const loadInitial = useCallback(async () => {
        if (isLoadingRef.current) return;

        isLoadingRef.current = true;
        setState('loading_initial');
        setError(null);
        seenIds.current.clear();

        try {
            const response = await fetchFunds();

            // De-duplicate and store
            const uniqueFunds = response.items.filter(fund => {
                if (seenIds.current.has(fund.fund_id)) return false;
                seenIds.current.add(fund.fund_id);
                return true;
            });

            setFunds(uniqueFunds);
            setNextCursor(response.next_cursor);
            setAsOfDate(response.as_of_date);
            setState(uniqueFunds.length === 0 ? 'idle' :
                response.next_cursor ? 'loaded' : 'end_of_results');
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load funds');
            setState('error_initial');
        } finally {
            isLoadingRef.current = false;
        }
    }, []);

    const loadMore = useCallback(async () => {
        if (isLoadingRef.current || !nextCursor) return;

        isLoadingRef.current = true;
        setState('loading_more');
        setError(null);

        try {
            const response = await fetchFunds(nextCursor);

            // De-duplicate and append
            const uniqueFunds = response.items.filter(fund => {
                if (seenIds.current.has(fund.fund_id)) return false;
                seenIds.current.add(fund.fund_id);
                return true;
            });

            setFunds(prev => [...prev, ...uniqueFunds]);
            setNextCursor(response.next_cursor);
            setState(response.next_cursor ? 'loaded' : 'end_of_results');
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load more funds');
            setState('error_load_more');
        } finally {
            isLoadingRef.current = false;
        }
    }, [nextCursor]);

    // Load initial data on first render
    const hasLoaded = useRef(false);
    if (!hasLoaded.current && state === 'idle') {
        hasLoaded.current = true;
        loadInitial();
    }

    // Render based on state
    if (state === 'loading_initial') {
        return (
            <div className={styles.container}>
                <header className={styles.header}>
                    <h1 className={styles.title}>Fund Catalog</h1>
                    <p className={styles.subtitle}>Explore mutual funds across all AMCs</p>
                </header>
                <SkeletonLoader count={6} />
            </div>
        );
    }

    if (state === 'error_initial') {
        return (
            <div className={styles.container}>
                <header className={styles.header}>
                    <h1 className={styles.title}>Fund Catalog</h1>
                </header>
                <ErrorState
                    message={error || 'Failed to load funds'}
                    onRetry={loadInitial}
                />
            </div>
        );
    }

    if (state === 'idle' && funds.length === 0 && !error) {
        // Still loading initial
        return (
            <div className={styles.container}>
                <header className={styles.header}>
                    <h1 className={styles.title}>Fund Catalog</h1>
                </header>
                <SkeletonLoader count={6} />
            </div>
        );
    }

    if (funds.length === 0) {
        return (
            <div className={styles.container}>
                <header className={styles.header}>
                    <h1 className={styles.title}>Fund Catalog</h1>
                </header>
                <EmptyState onRetry={loadInitial} />
            </div>
        );
    }

    return (
        <div className={styles.container}>
            <header className={styles.header}>
                <div className={styles.headerContent}>
                    <h1 className={styles.title}>Fund Catalog</h1>
                    <p className={styles.subtitle}>
                        Explore mutual funds across all AMCs
                    </p>
                </div>
                {asOfDate && (
                    <div className={styles.dateBadge}>
                        <span className={styles.dateLabel}>Data updated</span>
                        <span className={styles.dateValue}>{asOfDate}</span>
                    </div>
                )}
            </header>

            <div className={styles.stats}>
                <span>{funds.length} funds loaded</span>
            </div>

            <div className={styles.grid}>
                {funds.map((fund) => (
                    <FundCard key={fund.fund_id} fund={fund} />
                ))}
            </div>

            {/* Load more error - inline */}
            {state === 'error_load_more' && (
                <ErrorState
                    message={error || 'Failed to load more funds'}
                    onRetry={loadMore}
                    isInline
                />
            )}

            {/* Load more / End of results */}
            <div className={styles.loadMoreContainer}>
                <LoadMoreButton
                    onClick={loadMore}
                    isLoading={state === 'loading_more'}
                    isEndOfResults={state === 'end_of_results'}
                    hasError={state === 'error_load_more'}
                />
            </div>
        </div>
    );
}
