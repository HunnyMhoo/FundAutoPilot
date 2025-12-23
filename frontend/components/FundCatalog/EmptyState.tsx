'use client';

import styles from './EmptyState.module.css';

interface EmptyStateProps {
    onRetry: () => void;
    searchQuery?: string;
    onClearSearch?: () => void;
}

export function EmptyState({ onRetry, searchQuery, onClearSearch }: EmptyStateProps) {
    const isSearchEmpty = searchQuery && searchQuery.trim().length > 0;
    
    return (
        <div className={styles.container}>
            <div className={styles.icon}>{isSearchEmpty ? '🔍' : '📭'}</div>
            <h2 className={styles.title}>
                {isSearchEmpty ? `No funds match '${searchQuery}'` : 'No funds available'}
            </h2>
            <p className={styles.message}>
                {isSearchEmpty ? (
                    <>
                        We couldn't find any funds matching your search.
                        <br />
                        Try fund abbreviation or fewer keywords.
                    </>
                ) : (
                    <span>We couldn't find any funds at the moment. This might be temporary.</span>
                )}
            </p>
            <div className={styles.actions}>
                {isSearchEmpty && onClearSearch ? (
                    <button className={styles.primaryButton} onClick={onClearSearch}>
                        Clear search
                    </button>
                ) : (
                    <button className={styles.primaryButton} onClick={onRetry}>
                        Refresh
                    </button>
                )}
            </div>
        </div>
    );
}
