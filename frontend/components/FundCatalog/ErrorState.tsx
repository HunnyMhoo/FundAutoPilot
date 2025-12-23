import styles from './ErrorState.module.css';

interface ErrorStateProps {
    message?: string;
    onRetry: () => void;
    isInline?: boolean;
}

export function ErrorState({
    message = 'Something went wrong',
    onRetry,
    isInline = false
}: ErrorStateProps) {
    return (
        <div className={`${styles.container} ${isInline ? styles.inline : ''}`}>
            <div className={styles.icon}>⚠️</div>
            <p className={styles.message}>{message}</p>
            <button className={styles.retryButton} onClick={onRetry}>
                Try again
            </button>
        </div>
    );
}
