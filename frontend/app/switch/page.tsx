import { Metadata } from 'next';
import { SwitchPreviewPage } from '@/components/Switch/SwitchPreviewPage';

export const metadata: Metadata = {
    title: 'Switch Impact Preview | Fund Auto Pilot',
    description: 'Preview the impact of switching between mutual funds - fee, risk, and category changes',
};

interface SwitchPageProps {
    searchParams: Promise<{
        ids?: string;
    }>;
}

export default async function SwitchPage(props: SwitchPageProps) {
    const searchParams = await props.searchParams;
    const idsParam = searchParams.ids || '';
    
    return (
        <main>
            <SwitchPreviewPage idsParam={idsParam} />
        </main>
    );
}

