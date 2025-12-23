import styles from './LoadMoreButton.module.css';

interface LoadMoreButtonProps {
    onClick: () => void;
    isLoading: boolean;
    isEndOfResults: boolean;
    hasError: boolean;
}

export function LoadMoreButton({
    onClick,
    isLoading,
    isEndOfResults,
    hasError
}: LoadMoreButtonProps) {
    if (isEndOfResults) {
        return (
            <div className={styles.endOfResults}>
                <span className={styles.endIcon}>✓</span>
                End of results
            </div>
        );
    }

    return (
        <button
            className={`${styles.button} ${hasError ? styles.error : ''}`}
            onClick={onClick}
            disabled={isLoading}
        >
            {isLoading ? (
                <>
                    <span className={styles.spinner} />
                    Loading...
                </>
            ) : hasError ? (
                'Retry'
            ) : (
                'Load more'
            )}
        </button>
    );
}
