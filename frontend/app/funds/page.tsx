import { Metadata } from 'next';
import { FundCatalog } from '@/components/FundCatalog';

export const metadata: Metadata = {
    title: 'Fund Catalog | Switch Impact Simulator',
    description: 'Browse mutual funds across all Thai AMCs. Compare funds, check performance, and make informed investment decisions.',
};

export default function FundsPage() {
    return (
        <main>
            <FundCatalog />
        </main>
    );
}
