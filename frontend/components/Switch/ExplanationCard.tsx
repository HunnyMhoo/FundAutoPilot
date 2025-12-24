'use client';

import { SwitchPreviewResponse } from '@/types/switch';
import styles from './SwitchPreviewPage.module.css';

interface ExplanationCardProps {
    data: SwitchPreviewResponse;
}

export function ExplanationCard({ data }: ExplanationCardProps) {
    const { explainability } = data;
    
    return (
        <div className={styles.card}>
            <h3 className={styles.cardTitle}>Explanation</h3>
            <div className={styles.explanationContent}>
                <p className={styles.explanationParagraph}>
                    {explainability.rationale_paragraph}
                </p>
                
                {explainability.assumptions.length > 0 && (
                    <div className={styles.assumptions}>
                        <h4 className={styles.assumptionsTitle}>Assumptions:</h4>
                        <ul className={styles.assumptionsList}>
                            {explainability.assumptions.map((assumption, index) => (
                                <li key={index}>{assumption}</li>
                            ))}
                        </ul>
                    </div>
                )}
            </div>
        </div>
    );
}

