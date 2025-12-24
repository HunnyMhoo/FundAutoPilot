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
    // Decode URL-encoded characters (e.g., %26 -> &)
    const decodedFundId = decodeURIComponent(fundId);
    return {
        title: `Fund ${decodedFundId} | Switch Impact Simulator`,
        description: `View details for fund ${decodedFundId}`,
    };
}

export default async function FundDetailPage({ params }: FundDetailPageProps) {
    const { fundId } = await params;
    // Decode URL-encoded characters (e.g., %26 -> &)
    const decodedFundId = decodeURIComponent(fundId);

    return (
        <main>
            <FundDetailView fundId={decodedFundId} />
        </main>
    );
}
