'use client';

import { FundSummary } from '@/types/fund';
import { useSearchParams, usePathname } from 'next/navigation';
import Link from 'next/link';
import styles from './FundCard.module.css';

interface FundCardProps {
    fund: FundSummary;
}

export function FundCard({ fund }: FundCardProps) {
    const searchParams = useSearchParams();
    const pathname = usePathname();
    
    // Preserve current catalog state in URL for back navigation
    // Construct the 'from' URL with current query params
    const currentQuery = searchParams.toString();
    const fromUrl = currentQuery ? `${pathname}?${currentQuery}` : pathname;
    const detailUrl = `/funds/${fund.fund_id}?from=${encodeURIComponent(fromUrl)}`;
    
    return (
        <Link href={detailUrl} className={styles.card}>
            <div className={styles.header}>
                <h3 className={styles.name}>{fund.fund_name}</h3>
                <span className={styles.abbr}>{fund.fund_id}</span>
            </div>

            <div className={styles.meta}>
                <span className={styles.amc}>{fund.amc_name}</span>
                <span className={styles.separator}>•</span>
                <span className={styles.category}>
                    {fund.category || 'Not available'}
                </span>
            </div>

            <div className={styles.details}>
                <div className={styles.detail}>
                    <span className={styles.label}>Risk Level</span>
                    <span className={styles.value}>
                        {fund.risk_level || 'Not available'}
                    </span>
                </div>
                <div className={styles.detail}>
                    <span className={styles.label}>Expense Ratio</span>
                    <span className={styles.value}>
                        {fund.expense_ratio !== null
                            ? `${fund.expense_ratio.toFixed(2)}%`
                            : 'Not available'}
                    </span>
                </div>
            </div>
        </Link>
    );
}
