'use client';

import { SwitchPreviewResponse } from '@/types/switch';
import styles from './SwitchPreviewPage.module.css';

interface FeeImpactCardProps {
    data: SwitchPreviewResponse;
}

export function FeeImpactCard({ data }: FeeImpactCardProps) {
    const { inputs_echo, deltas, explainability } = data;
    
    if (deltas.annual_fee_thb_delta === null) {
        return (
            <div className={styles.card}>
                <h3 className={styles.cardTitle}>Fee Impact</h3>
                <div className={styles.notAvailable}>
                    <p>Fee impact cannot be calculated due to missing expense ratio data.</p>
                </div>
            </div>
        );
    }
    
    const isPositive = deltas.annual_fee_thb_delta > 0;
    const isNegative = deltas.annual_fee_thb_delta < 0;
    const isZero = deltas.annual_fee_thb_delta === 0;
    
    return (
        <div className={styles.card}>
            <h3 className={styles.cardTitle}>Estimated Annual Fee Drag Difference</h3>
            
            <div className={styles.formulaBox}>
                <code className={styles.formula}>{explainability.formula_display}</code>
            </div>
            
            <div className={styles.feeDetails}>
                <div className={styles.feeRow}>
                    <span className={styles.feeLabel}>Current Expense Ratio:</span>
                    <span className={styles.feeValue}>
                        {inputs_echo.current_expense_ratio?.toFixed(2)}%
                    </span>
                </div>
                <div className={styles.feeRow}>
                    <span className={styles.feeLabel}>Target Expense Ratio:</span>
                    <span className={styles.feeValue}>
                        {inputs_echo.target_expense_ratio?.toFixed(2)}%
                    </span>
                </div>
                <div className={styles.feeRow}>
                    <span className={styles.feeLabel}>Amount:</span>
                    <span className={styles.feeValue}>
                        {inputs_echo.amount_thb.toLocaleString('en-US')} THB
                    </span>
                </div>
            </div>
            
            <div className={styles.resultBox}>
                <div className={styles.resultLabel}>Annual Fee Difference:</div>
                <div className={`${styles.resultValue} ${
                    isPositive ? styles.positive : isNegative ? styles.negative : styles.zero
                }`}>
                    {isPositive && '+'}
                    {Math.abs(deltas.annual_fee_thb_delta).toLocaleString('en-US')} THB/year
                </div>
                <div className={styles.resultNote}>
                    (Rounded to nearest THB)
                </div>
            </div>
        </div>
    );
}

