'use client';

import { FundDetail } from '@/types/fund';
import styles from './FreshnessBadge.module.css';

interface FreshnessBadgeProps {
    fund: FundDetail;
}

export function FreshnessBadge({ fund }: FreshnessBadgeProps) {
    const formatDate = (dateStr: string | null): string => {
        if (!dateStr) return '';
        try {
            const date = new Date(dateStr);
            return date.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
            });
        } catch {
            return dateStr;
        }
    };

    const primaryDate = fund.as_of_date || fund.last_updated_at;
    const secondaryDate = fund.as_of_date && fund.last_updated_at 
        ? (fund.as_of_date === fund.last_updated_at?.split('T')[0] ? null : fund.last_updated_at)
        : null;

    if (!primaryDate) {
        return null;
    }

    return (
        <div className={styles.badge}>
            <div className={styles.badgeContent}>
                <span className={styles.label}>Data as of</span>
                <span className={styles.date}>{formatDate(primaryDate)}</span>
                {secondaryDate && (
                    <span className={styles.secondaryDate}>
                        (Updated: {formatDate(secondaryDate)})
                    </span>
                )}
            </div>
            {fund.data_source && (
                <div className={styles.source}>
                    Source: {fund.data_source}
                </div>
            )}
        </div>
    );
}

