'use client';

import { MetaResponse } from '@/utils/api/funds';
import styles from './StatsCard.module.css';

interface StatsCardProps {
    meta: MetaResponse | null;
    isLoading: boolean;
    error: string | null;
}

export function StatsCard({ meta, isLoading, error }: StatsCardProps) {
    const formatDate = (dateStr: string): string => {
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

    if (isLoading) {
        return (
            <div className={styles.card}>
                <div className={styles.skeleton}>
                    <div className={styles.skeletonLine}></div>
                    <div className={styles.skeletonLine}></div>
                </div>
            </div>
        );
    }

    if (error || !meta) {
        return (
            <div className={styles.card}>
                <div className={styles.stat}>
                    <span className={styles.statLabel}>Total funds</span>
                    <span className={styles.statValue}>—</span>
                </div>
                <div className={styles.stat}>
                    <span className={styles.statLabel}>Data updated</span>
                    <span className={styles.statValue}>—</span>
                </div>
            </div>
        );
    }

    return (
        <div className={styles.card}>
            <div className={styles.stat}>
                <span className={styles.statLabel}>Total funds</span>
                <span className={styles.statValue}>{meta.total_fund_count.toLocaleString()}</span>
            </div>
            <div className={styles.stat}>
                <span className={styles.statLabel}>Data updated</span>
                <span className={styles.statValue}>{formatDate(meta.data_as_of)}</span>
            </div>
        </div>
    );
}

