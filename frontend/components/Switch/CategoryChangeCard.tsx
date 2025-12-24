'use client';

import { SwitchPreviewResponse } from '@/types/switch';
import styles from './SwitchPreviewPage.module.css';

interface CategoryChangeCardProps {
    data: SwitchPreviewResponse;
}

export function CategoryChangeCard({ data }: CategoryChangeCardProps) {
    const { inputs_echo, deltas } = data;
    
    if (deltas.category_changed === null) {
        return (
            <div className={styles.card}>
                <h3 className={styles.cardTitle}>Category Change</h3>
                <div className={styles.notAvailable}>
                    <p>Category information is not available for one or both funds.</p>
                </div>
            </div>
        );
    }
    
    return (
        <div className={styles.card}>
            <h3 className={styles.cardTitle}>Category Change</h3>
            <div className={styles.categoryDisplay}>
                <div className={styles.categoryValue}>{inputs_echo.current_category || 'N/A'}</div>
                <div className={styles.arrow}>→</div>
                <div className={styles.categoryValue}>{inputs_echo.target_category || 'N/A'}</div>
            </div>
            {deltas.category_changed && (
                <div className={styles.categoryNote}>
                    Category shift may affect diversification characteristics.
                </div>
            )}
            {!deltas.category_changed && (
                <div className={styles.categoryNote}>
                    Category remains the same, maintaining similar diversification.
                </div>
            )}
        </div>
    );
}

