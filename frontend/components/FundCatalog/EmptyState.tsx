import styles from './EmptyState.module.css';

interface EmptyStateProps {
    onRetry: () => void;
}

export function EmptyState({ onRetry }: EmptyStateProps) {
    return (
        <div className={styles.container}>
            <div className={styles.icon}>📭</div>
            <h2 className={styles.title}>No funds available</h2>
            <p className={styles.message}>
                We couldn't find any funds at the moment. This might be temporary.
            </p>
            <button className={styles.retryButton} onClick={onRetry}>
                Refresh
            </button>
        </div>
    );
}
