'use client';

import { FundDetail } from '@/types/fund';
import styles from './KeyFactsCard.module.css';

interface KeyFactsCardProps {
    fund: FundDetail;
}

export function KeyFactsCard({ fund }: KeyFactsCardProps) {
    return (
        <div className={styles.card}>
            <h2 className={styles.title}>Key Facts</h2>
            <div className={styles.facts}>
                <div className={styles.fact}>
                    <div className={styles.factLabel}>Risk Level</div>
                    <div className={styles.factValue}>
                        {fund.risk_level ? (
                            <span>{fund.risk_level}</span>
                        ) : (
                            <span className={styles.notAvailable}>
                                Not available
                                <span className={styles.tooltip}>
                                    Risk level not provided in current dataset.
                                </span>
                            </span>
                        )}
                    </div>
                </div>
                <div className={styles.fact}>
                    <div className={styles.factLabel}>Expense Ratio</div>
                    <div className={styles.factValue}>
                        {fund.expense_ratio !== null ? (
                            <span>{fund.expense_ratio.toFixed(3)}%</span>
                        ) : (
                            <span className={styles.notAvailable}>
                                Not available
                                <span className={styles.tooltip}>
                                    Fee data not available for this fund yet.
                                </span>
                            </span>
                        )}
                    </div>
                </div>
            </div>
            {(fund.risk_level === null || fund.expense_ratio === null) && (
                <div className={styles.coverageNote}>
                    Some data fields are still being populated.
                </div>
            )}
        </div>
    );
}

