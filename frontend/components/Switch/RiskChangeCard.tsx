'use client';

import { SwitchPreviewResponse } from '@/types/switch';
import styles from './SwitchPreviewPage.module.css';

interface RiskChangeCardProps {
    data: SwitchPreviewResponse;
}

export function RiskChangeCard({ data }: RiskChangeCardProps) {
    const { inputs_echo, deltas } = data;
    
    if (deltas.risk_level_delta === null) {
        return (
            <div className={styles.card}>
                <h3 className={styles.cardTitle}>Risk Level Change</h3>
                <div className={styles.notAvailable}>
                    <p>Risk level information is not available for one or both funds.</p>
                </div>
            </div>
        );
    }
    
    const isPositive = deltas.risk_level_delta > 0;
    const isNegative = deltas.risk_level_delta < 0;
    const isZero = deltas.risk_level_delta === 0;
    
    let badgeText = 'Same';
    let badgeClass = styles.badgeSame;
    
    if (isPositive) {
        badgeText = 'Up';
        badgeClass = styles.badgeUp;
    } else if (isNegative) {
        badgeText = 'Down';
        badgeClass = styles.badgeDown;
    }
    
    return (
        <div className={styles.card}>
            <h3 className={styles.cardTitle}>Risk Level Change</h3>
            <div className={styles.riskDisplay}>
                <div className={styles.riskValue}>{inputs_echo.current_risk_level}</div>
                <div className={styles.arrow}>→</div>
                <div className={styles.riskValue}>{inputs_echo.target_risk_level}</div>
                <div className={`${styles.badge} ${badgeClass}`}>{badgeText}</div>
            </div>
            {!isZero && (
                <div className={styles.riskNote}>
                    {isPositive 
                        ? 'Higher risk exposure' 
                        : 'Lower risk exposure'}
                </div>
            )}
        </div>
    );
}

