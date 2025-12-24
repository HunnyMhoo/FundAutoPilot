'use client';

import { FundDetail } from '@/types/fund';
import styles from './KeyFactsCard.module.css';

interface KeyFactsCardProps {
    fund: FundDetail;
}

export function KeyFactsCard({ fund }: KeyFactsCardProps) {
    // Determine if AIMC category is from fallback source
    const isAimcFallback = fund.aimc_category_source === 'SEC_API';
    
    return (
        <div className={styles.card}>
            {/* Tier 1: Hero Info */}
            <h2 className={styles.title}>Fund Classification</h2>
            <div className={styles.heroGrid}>
                <div className={styles.heroItem}>
                    <div className={styles.heroLabel}>Risk Level</div>
                    <div className={styles.heroValue}>
                        {fund.risk_level ? (
                            <span className={styles.riskBadge}>{fund.risk_level}</span>
                        ) : (
                            <span className={styles.notAvailable}>—</span>
                        )}
                    </div>
                </div>
                <div className={styles.heroItem}>
                    <div className={styles.heroLabel}>AIMC Type</div>
                    <div className={styles.heroValue}>
                        {fund.aimc_category ? (
                            <span className={styles.aimcCategory}>
                                {fund.aimc_category}
                                {isAimcFallback && (
                                    <span className={styles.fallbackIndicator} title="Derived from SEC classification">*</span>
                                )}
                            </span>
                        ) : (
                            <span className={styles.notAvailable}>—</span>
                        )}
                    </div>
                </div>
                <div className={styles.heroItem}>
                    <div className={styles.heroLabel}>Expense Ratio</div>
                    <div className={styles.heroValue}>
                        {fund.expense_ratio !== null ? (
                            <span>{fund.expense_ratio.toFixed(2)}%</span>
                        ) : (
                            <span className={styles.notAvailable}>—</span>
                        )}
                    </div>
                </div>
            </div>

            {/* Tier 2: Investment Requirements */}
            {(fund.min_investment || fund.min_redemption || fund.min_balance || fund.redemption_period) && (
                <>
                    <h2 className={styles.sectionTitle}>Investment Requirements</h2>
                    <div className={styles.facts}>
                        {fund.min_investment && (
                            <div className={styles.fact}>
                                <div className={styles.factLabel}>Minimum Investment</div>
                                <div className={styles.factValue}>{fund.min_investment}</div>
                            </div>
                        )}
                        {fund.min_redemption && (
                            <div className={styles.fact}>
                                <div className={styles.factLabel}>Minimum Redemption</div>
                                <div className={styles.factValue}>{fund.min_redemption}</div>
                            </div>
                        )}
                        {fund.min_balance && (
                            <div className={styles.fact}>
                                <div className={styles.factLabel}>Minimum Balance</div>
                                <div className={styles.factValue}>{fund.min_balance}</div>
                            </div>
                        )}
                        {fund.redemption_period && (
                            <div className={styles.fact}>
                                <div className={styles.factLabel}>Redemption</div>
                                <div className={styles.factValue}>{fund.redemption_period}</div>
                            </div>
                        )}
                    </div>
                </>
            )}

            {/* Fallback note */}
            {isAimcFallback && (
                <div className={styles.coverageNote}>
                    * AIMC category derived from SEC fund classification
                </div>
            )}
        </div>
    );
}

