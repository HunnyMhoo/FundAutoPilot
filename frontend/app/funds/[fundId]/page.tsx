import { Metadata } from 'next';
import { FundDetailView } from '@/components/FundDetail/FundDetailView';

interface FundDetailPageProps {
    params: Promise<{
        fundId: string;
    }>;
    searchParams: Promise<{
        from?: string;
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
        <main>
            <FundDetailView fundId={fundId} />
        </main>
    );
}
