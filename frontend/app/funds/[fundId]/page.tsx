import { Metadata } from 'next';
import Link from 'next/link';
import styles from './page.module.css';

interface FundDetailPageProps {
    params: Promise<{
        fundId: string;
    }>;
}

export async function generateMetadata({ params }: FundDetailPageProps): Promise<Metadata> {
    const { fundId } = await params;
    return {
        title: `Fund ${fundId} | Switch Impact Simulator`,
        description: `View details for fund ${fundId}`,
    };
}

export default async function FundDetailPage({ params }: FundDetailPageProps) {
    const { fundId } = await params;

    return (
        <main className={styles.container}>
            <Link href="/funds" className={styles.backLink}>
                ← Back to Catalog
            </Link>

            <div className={styles.placeholder}>
                <h1 className={styles.title}>Fund Details</h1>
                <p className={styles.fundId}>{fundId}</p>
                <p className={styles.message}>
                    Full fund details will be available in US4.
                </p>
            </div>
        </main>
    );
}
