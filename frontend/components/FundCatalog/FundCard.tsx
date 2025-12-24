'use client';

import { FundSummary } from '@/types/fund';
import { useSearchParams, usePathname } from 'next/navigation';
import Link from 'next/link';
import { useCompareState } from '@/components/Compare';
import styles from './FundCard.module.css';

interface FundCardProps {
    fund: FundSummary;
}

export function FundCard({ fund }: FundCardProps) {
    const searchParams = useSearchParams();
    const pathname = usePathname();
    const { selectedIds, addFund, isAtMax } = useCompareState();
    
    // Preserve current catalog state in URL for back navigation
    // Construct the 'from' URL with current query params
    const currentQuery = searchParams.toString();
    const fromUrl = currentQuery ? `${pathname}?${currentQuery}` : pathname;
    const detailUrl = `/funds/${fund.fund_id}?from=${encodeURIComponent(fromUrl)}`;
    
    const isSelected = selectedIds.includes(fund.fund_id);
    const canAdd = !isSelected && !isAtMax;
    
    const handleAddToCompare = (e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (canAdd) {
            const added = addFund(fund.fund_id);
            if (!added && isAtMax) {
                // Show a message or toast that max is reached
                alert('Compare supports up to 3 funds. Remove one to add another.');
            }
        }
    };
    
    return (
        <div className={styles.cardWrapper}>
            <Link href={detailUrl} className={styles.card}>
                <div className={styles.header}>
                    <h3 className={styles.name}>{fund.fund_name}</h3>
                    <button
                        className={styles.compareButton}
                        onClick={handleAddToCompare}
                        disabled={!canAdd}
                        title={isSelected ? 'Already in compare' : isAtMax ? 'Maximum 3 funds in compare' : 'Add to compare'}
                        aria-label={isSelected ? 'Already in compare' : isAtMax ? 'Maximum 3 funds in compare' : 'Add to compare'}
                    >
                        {isSelected ? '✓' : '+'}
                    </button>
                </div>

                <div className={styles.meta}>
                    <span className={styles.amc}>{fund.amc_name}</span>
                    {fund.category && (
                        <>
                            <span className={styles.separator}>•</span>
                            <span className={styles.category}>{fund.category}</span>
                        </>
                    )}
                </div>

                <div className={styles.details}>
                    <div className={styles.detail}>
                        <span className={styles.label}>Risk</span>
                        <span className={styles.value}>
                            {fund.risk_level ? (
                                <span>{fund.risk_level}</span>
                            ) : (
                                <span title="Not available from SEC dataset for this fund">—</span>
                            )}
                        </span>
                    </div>
                    <div className={styles.detail}>
                        <span className={styles.label}>AIMC Type</span>
                        <span className={styles.value}>
                            {fund.aimc_category ? (
                                <span className={styles.aimcType}>
                                    {fund.aimc_category}
                                    {fund.aimc_category_source === 'SEC_API' && (
                                        <span className={styles.fallbackMark} title="Derived from SEC classification">*</span>
                                    )}
                                </span>
                            ) : (
                                <span title="Not available">—</span>
                            )}
                        </span>
                    </div>
                </div>
            </Link>
        </div>
    );
}
