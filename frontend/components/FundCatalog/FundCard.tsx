'use client';

import { FundSummary } from '@/types/fund';
import { useSearchParams, usePathname } from 'next/navigation';
import Link from 'next/link';
import { useCompareState } from '@/components/Compare';
import styles from './FundCard.module.css';

interface FundCardProps {
    fund: FundSummary;
}

/**
 * Format category label with focus (US-N13).
 * Format: "AIMC Type (Focus)" when focus available, "AIMC Type" when focus unavailable.
 */
function formatCategoryLabel(aimcCategory: string | null, peerFocus: string | null): string {
    if (!aimcCategory) {
        return '—';
    }
    
    // peer_focus is exact copy of aimc_category, so if they're the same, don't duplicate
    // Only show focus if it's different from category (though per US-N9, they should be the same)
    if (peerFocus && peerFocus !== aimcCategory) {
        return `${aimcCategory} (${peerFocus})`;
    }
    
    return aimcCategory;
}

/**
 * Format return value for display (US-N10, US-N13).
 * Format: "1Y: +X.X%" or "YTD: +X.X%" with appropriate sign.
 * Returns null if no return data available.
 */
function formatReturn(
    trailing1y: number | null,
    ytd: number | null
): { label: string; value: string; isPositive: boolean } | null {
    // Prefer 1Y return, fallback to YTD
    const returnValue = trailing1y ?? ytd;
    const horizon = trailing1y !== null ? '1Y' : 'YTD';
    
    if (returnValue === null || returnValue === undefined) {
        return null;
    }
    
    const isPositive = returnValue >= 0;
    const sign = isPositive ? '+' : '';
    const formattedValue = `${sign}${returnValue.toFixed(1)}%`;
    
    return {
        label: horizon,
        value: formattedValue,
        isPositive,
    };
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
    
    // Note: dividend_policy and management_style are only available from Fund Detail API
    // They require SEC API calls which are too slow for list views
    // These badges will be shown on Fund Detail page instead
    
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
                                    {/* US-N13: Display category with focus if available */}
                                    {formatCategoryLabel(fund.aimc_category, fund.peer_focus)}
                                    {fund.aimc_category_source === 'SEC_API' && (
                                        <span className={styles.fallbackMark} title="Derived from SEC classification">*</span>
                                    )}
                                </span>
                            ) : (
                                <span title="Not available">—</span>
                            )}
                        </span>
                    </div>
                    {/* US-N10, US-N13: Display absolute return */}
                    {(() => {
                        const returnData = formatReturn(fund.trailing_1y_return, fund.ytd_return);
                        if (!returnData) {
                            return null;
                        }
                        return (
                            <div className={styles.detail}>
                                <span className={styles.label}>Return</span>
                                <span className={`${styles.value} ${styles.returnValue} ${returnData.isPositive ? styles.returnPositive : styles.returnNegative}`}>
                                    <span className={styles.returnHorizon}>{returnData.label}:</span>
                                    <span className={styles.returnAmount}>{returnData.value}</span>
                                </span>
                            </div>
                        );
                    })()}
                </div>
            </Link>
        </div>
    );
}
