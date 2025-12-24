'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { fetchSwitchPreview, SwitchPreviewRequest } from '@/utils/api/switch';
import { SwitchPreviewResponse } from '@/types/switch';
import { CompareFundsResponse } from '@/types/fund';
import { fetchCompareFunds } from '@/utils/api/funds';
import { FeeImpactCard } from './FeeImpactCard';
import { RiskChangeCard } from './RiskChangeCard';
import { CategoryChangeCard } from './CategoryChangeCard';
import { ExplanationCard } from './ExplanationCard';
import { ErrorState } from '@/components/FundCatalog/ErrorState';
import styles from './SwitchPreviewPage.module.css';

type SwitchState = 'idle' | 'loading' | 'loaded' | 'error' | 'blocked';

interface SwitchPreviewPageProps {
    idsParam: string;
}

export function SwitchPreviewPage({ idsParam }: SwitchPreviewPageProps) {
    const router = useRouter();
    
    const [state, setState] = useState<SwitchState>('idle');
    const [data, setData] = useState<SwitchPreviewResponse | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [comparedFunds, setComparedFunds] = useState<CompareFundsResponse | null>(null);
    
    // Form state
    const [currentFundId, setCurrentFundId] = useState<string>('');
    const [targetFundId, setTargetFundId] = useState<string>('');
    const [amount, setAmount] = useState<number>(100000);
    
    // Load compared funds from URL params
    useEffect(() => {
        if (!idsParam) {
            setError('No funds selected. Please go back to Compare page.');
            setState('error');
            return;
        }
        
        const ids = idsParam
            .split(',')
            .map(id => id.trim())
            .filter(id => id.length > 0);
        
        if (ids.length < 2) {
            setError('Please select at least 2 funds to compare.');
            setState('error');
            return;
        }
        
        // Fetch compared funds to populate dropdowns
        const loadComparedFunds = async () => {
            try {
                const response = await fetchCompareFunds(ids);
                setComparedFunds(response);
                
                // Pre-select first two funds
                if (response.funds.length >= 2) {
                    setCurrentFundId(response.funds[0].fund_id);
                    setTargetFundId(response.funds[1].fund_id);
                }
            } catch (err) {
                const errorMessage = err instanceof Error ? err.message : 'Failed to load funds';
                setError(errorMessage);
                setState('error');
            }
        };
        
        loadComparedFunds();
    }, [idsParam]);
    
    const handleGeneratePreview = async () => {
        if (!currentFundId || !targetFundId || amount <= 0) {
            return;
        }
        
        if (currentFundId === targetFundId) {
            setError('Current and target funds must be different.');
            return;
        }
        
        setState('loading');
        setError(null);
        
        try {
            const request: SwitchPreviewRequest = {
                current_fund_id: currentFundId,
                target_fund_id: targetFundId,
                amount_thb: amount,
            };
            
            const response = await fetchSwitchPreview(request);
            setData(response);
            
            if (response.coverage.status === 'BLOCKED') {
                setState('blocked');
            } else {
                setState('loaded');
            }
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Failed to generate preview';
            setError(errorMessage);
            setState('error');
        }
    };
    
    const isFormValid = currentFundId && targetFundId && currentFundId !== targetFundId && amount >= 1000 && amount <= 1000000000;
    
    if (state === 'error' && !comparedFunds) {
        return (
            <div className={styles.container}>
                <div className={styles.header}>
                    <h1 className={styles.title}>Switch Impact Preview</h1>
                </div>
                <ErrorState message={error || 'Failed to load funds'} onRetry={() => router.push('/compare')} />
            </div>
        );
    }
    
    return (
        <div className={styles.container}>
            <div className={styles.header}>
                <h1 className={styles.title}>Switch Impact Preview</h1>
                <p className={styles.subtitle}>
                    Understand the trade-offs before switching funds
                </p>
            </div>
            
            <div className={styles.layout}>
                {/* Form Panel */}
                <div className={styles.formPanel}>
                    <h2 className={styles.panelTitle}>Switch Configuration</h2>
                    
                    <div className={styles.formGroup}>
                        <label htmlFor="current-fund" className={styles.label}>
                            Current Fund *
                        </label>
                        <select
                            id="current-fund"
                            className={styles.select}
                            value={currentFundId}
                            onChange={(e) => setCurrentFundId(e.target.value)}
                        >
                            <option value="">Select current fund</option>
                            {comparedFunds?.funds.map((fund) => (
                                <option key={fund.fund_id} value={fund.fund_id}>
                                    {fund.identity.fund_name}
                                </option>
                            ))}
                        </select>
                    </div>
                    
                    <div className={styles.formGroup}>
                        <label htmlFor="target-fund" className={styles.label}>
                            Target Fund *
                        </label>
                        <select
                            id="target-fund"
                            className={styles.select}
                            value={targetFundId}
                            onChange={(e) => setTargetFundId(e.target.value)}
                        >
                            <option value="">Select target fund</option>
                            {comparedFunds?.funds.map((fund) => (
                                <option key={fund.fund_id} value={fund.fund_id}>
                                    {fund.identity.fund_name}
                                </option>
                            ))}
                        </select>
                    </div>
                    
                    <div className={styles.formGroup}>
                        <label htmlFor="amount" className={styles.label}>
                            Investment Amount (THB) *
                        </label>
                        <input
                            id="amount"
                            type="number"
                            className={styles.input}
                            value={amount}
                            onChange={(e) => setAmount(parseFloat(e.target.value) || 0)}
                            min={1000}
                            max={1000000000}
                            step={1000}
                        />
                        <div className={styles.inputHint}>
                            Minimum: 1,000 THB | Maximum: 1,000,000,000 THB
                        </div>
                    </div>
                    
                    <button
                        className={`${styles.generateButton} ${!isFormValid ? styles.disabled : ''}`}
                        onClick={handleGeneratePreview}
                        disabled={!isFormValid || state === 'loading'}
                    >
                        {state === 'loading' ? 'Generating...' : 'Generate Preview'}
                    </button>
                    
                    {currentFundId === targetFundId && currentFundId && (
                        <div className={styles.validationError}>
                            Current and target funds must be different.
                        </div>
                    )}
                </div>
                
                {/* Results Panel */}
                <div className={styles.resultsPanel}>
                    {state === 'idle' && (
                        <div className={styles.emptyState}>
                            <p>Fill in the form and click "Generate Preview" to see the switch impact.</p>
                        </div>
                    )}
                    
                    {state === 'loading' && (
                        <div className={styles.loadingState}>
                            <p>Generating preview...</p>
                        </div>
                    )}
                    
                    {state === 'error' && error && (
                        <ErrorState message={error} onRetry={handleGeneratePreview} />
                    )}
                    
                    {state === 'blocked' && data && (
                        <div className={styles.blockedState}>
                            <h3 className={styles.blockedTitle}>Preview Blocked</h3>
                            <p className={styles.blockedMessage}>
                                {data.coverage.blocking_reason || 'Required data is missing.'}
                            </p>
                            {data.coverage.missing_fields.length > 0 && (
                                <div className={styles.missingFields}>
                                    <strong>Missing fields:</strong>
                                    <ul>
                                        {data.coverage.missing_fields.map((field, index) => (
                                            <li key={index}>{field}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                            {data.coverage.suggested_next_action && (
                                <p className={styles.suggestedAction}>
                                    <strong>Suggestion:</strong> {data.coverage.suggested_next_action}
                                </p>
                            )}
                        </div>
                    )}
                    
                    {state === 'loaded' && data && (
                        <>
                            <div className={styles.resultsGrid}>
                                <FeeImpactCard data={data} />
                                <RiskChangeCard data={data} />
                                <CategoryChangeCard data={data} />
                                <ExplanationCard data={data} />
                            </div>
                            
                            {/* Disclaimers */}
                            <div className={styles.disclaimers}>
                                {data.explainability.disclaimers.map((disclaimer, index) => (
                                    <p key={index} className={styles.disclaimer}>
                                        {disclaimer}
                                    </p>
                                ))}
                            </div>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}

