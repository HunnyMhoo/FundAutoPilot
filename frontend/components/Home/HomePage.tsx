'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { fetchMeta, MetaResponse } from '@/utils/api/funds';
import { StatsCard } from './StatsCard';
import styles from './HomePage.module.css';

export function HomePage() {
    const [meta, setMeta] = useState<MetaResponse | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const loadMeta = async () => {
            setIsLoading(true);
            setError(null);
            try {
                const data = await fetchMeta();
                setMeta(data);
            } catch (err) {
                setError(err instanceof Error ? err.message : 'Failed to load stats');
                // Don't block the page - still show value prop and CTA
            } finally {
                setIsLoading(false);
            }
        };

        loadMeta();
    }, []);

    return (
        <div className={styles.container}>
            <main className={styles.main}>
                <div className={styles.hero}>
                    <h1 className={styles.title}>Fund Auto Pilot</h1>
                    <p className={styles.valueProp}>
                        Browse funds across AMCs, compare candidates, and preview the impact of switching—before you commit.
                    </p>
                    <StatsCard meta={meta} isLoading={isLoading} error={error} />
                    <div className={styles.ctaGroup}>
                        <Link href="/funds" className={styles.primaryCta}>
                            Browse funds
                        </Link>
                        {/* Secondary CTA hidden until US-N7 is ready */}
                        {/* <Link href="/switch" className={styles.secondaryCta}>
                            Try switch preview
                        </Link> */}
                    </div>
                </div>
            </main>
        </div>
    );
}

