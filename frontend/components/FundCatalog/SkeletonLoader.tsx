import styles from './SkeletonLoader.module.css';

interface SkeletonLoaderProps {
    count?: number;
}

export function SkeletonLoader({ count = 6 }: SkeletonLoaderProps) {
    return (
        <div className={styles.container}>
            {Array.from({ length: count }).map((_, i) => (
                <div key={i} className={styles.card}>
                    <div className={styles.header}>
                        <div className={styles.titleSkeleton} />
                        <div className={styles.badgeSkeleton} />
                    </div>
                    <div className={styles.metaSkeleton} />
                    <div className={styles.details}>
                        <div className={styles.detailSkeleton} />
                        <div className={styles.detailSkeleton} />
                    </div>
                </div>
            ))}
        </div>
    );
}
