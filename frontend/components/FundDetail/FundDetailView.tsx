'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { FundDetail } from '@/types/fund';
import { fetchFundDetail } from '@/utils/api/funds';
import { KeyFactsCard } from './KeyFactsCard';
import { FreshnessBadge } from './FreshnessBadge';
import { ErrorState } from '@/components/FundCatalog/ErrorState';
import styles from './FundDetailView.module.css';

interface FundDetailViewProps {
    fundId: string;
}

type DetailState = 'loading' | 'loaded' | 'error' | 'not_found';

export function FundDetailView({ fundId }: FundDetailViewProps) {
    const router = useRouter();
    const searchParams = useSearchParams();
    const [fund, setFund] = useState<FundDetail | null>(null);
    const [state, setState] = useState<DetailState>('loading');
    const [error, setError] = useState<string | null>(null);

    // Get the 'from' query param for back navigation
    const fromUrl = searchParams.get('from') || '/funds';

    useEffect(() => {
        let isMounted = true;

        const loadFund = async () => {
            setState('loading');
            setError(null);

            try {
                const data = await fetchFundDetail(fundId);
                if (isMounted) {
                    setFund(data);
                    setState('loaded');
                }
            } catch (err) {
                if (isMounted) {
                    const errorMessage = err instanceof Error ? err.message : 'Failed to load fund details';
                    setError(errorMessage);
                    
                    if (errorMessage.toLowerCase().includes('not found')) {
                        setState('not_found');
                    } else {
                        setState('error');
                    }
                }
            }
        };

        loadFund();

        return () => {
            isMounted = false;
        };
    }, [fundId]);

    const handleRetry = () => {
        setState('loading');
        setError(null);
        // Retry by reloading
        fetchFundDetail(fundId)
            .then((data) => {
                setFund(data);
                setState('loaded');
            })
            .catch((err) => {
                const errorMessage = err instanceof Error ? err.message : 'Failed to load fund details';
                setError(errorMessage);
                if (errorMessage.toLowerCase().includes('not found')) {
                    setState('not_found');
                } else {
                    setState('error');
                }
            });
    };

    // Loading state
    if (state === 'loading') {
        return (
            <div className={styles.container}>
                <Link href={fromUrl} className={styles.backLink}>
                    ← Back to Catalog
                </Link>
                <div className={styles.skeleton}>
                    <div className={styles.skeletonHeader}></div>
                    <div className={styles.skeletonContent}></div>
                </div>
            </div>
        );
    }

    // 404 state
    if (state === 'not_found') {
        return (
            <div className={styles.container}>
                <Link href={fromUrl} className={styles.backLink}>
                    ← Back to Catalog
                </Link>
                <div className={styles.notFound}>
                    <h1 className={styles.notFoundTitle}>Fund not found</h1>
                    <p className={styles.notFoundMessage}>
                        The fund with ID <code>{fundId}</code> could not be found.
                    </p>
                    <Link href={fromUrl} className={styles.backButton}>
                        Back to Catalog
                    </Link>
                </div>
            </div>
        );
    }

    // Error state
    if (state === 'error') {
        return (
            <div className={styles.container}>
                <Link href={fromUrl} className={styles.backLink}>
                    ← Back to Catalog
                </Link>
                <ErrorState message={error || 'Failed to load fund details'} onRetry={handleRetry} />
            </div>
        );
    }

    // Loaded state
    if (!fund) {
        return null;
    }

    return (
        <div className={styles.container}>
            <Link href={fromUrl} className={styles.backLink}>
                ← Back to Catalog
            </Link>

            <div className={styles.header}>
                <div className={styles.headerContent}>
                    <h1 className={styles.title}>{fund.fund_name}</h1>
                    {fund.fund_abbr && (
                        <span className={styles.abbr}>{fund.fund_abbr}</span>
                    )}
                </div>
            </div>

            <div className={styles.contextRow}>
                <span className={styles.amc}>{fund.amc_name}</span>
                {fund.category && (
                    <>
                        <span className={styles.separator}>•</span>
                        <span className={styles.category}>{fund.category}</span>
                    </>
                )}
            </div>

            <FreshnessBadge fund={fund} />
            <KeyFactsCard fund={fund} />
        </div>
    );
}

