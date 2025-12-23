import { FilterSection } from './FilterSection';
import { FundFilters } from '@/utils/api/funds';

interface FilterPanelProps {
    filters: FundFilters;
    onToggle: (type: keyof FundFilters, value: string) => void;
    className?: string;
}

// Hardcoded for MVP - typically fetched from Facets API
const CATEGORIES = [
    { label: 'Equity', value: 'Equity' },
    { label: 'Fixed Income', value: 'Fixed Income' },
    { label: 'Mixed', value: 'Mixed' },
    { label: 'Alternative', value: 'Alternative' },
    // Add more actual values from DB inspection later
];

const RISKS = [
    { label: 'Level 1 - Low', value: '1' },
    { label: 'Level 2', value: '2' },
    { label: 'Level 3', value: '3' },
    { label: 'Level 4', value: '4' },
    { label: 'Level 5', value: '5' },
    { label: 'Level 6', value: '6' },
    { label: 'Level 7', value: '7' },
    { label: 'Level 8 - High', value: '8' },
];

const FEE_BANDS = [
    { label: 'Low (≤ 1.0%)', value: 'low' },
    { label: 'Medium (1-2%)', value: 'medium' },
    { label: 'High (> 2.0%)', value: 'high' },
];

const TOP_AMCS = [
    // Top 5-10 for MVP
    { label: 'SCBAM', value: 'SCBAM' }, // Need actual IDs! Using Code for now based on typical usage
    { label: 'KAsset', value: 'KAsset' },
    { label: 'BBLAM', value: 'BBLAM' },
    { label: 'Krungsri', value: 'Krungsri' },
    { label: 'Kiatnakin', value: 'Kiatnakin' },
];

export function FilterPanel({ filters, onToggle, className = '' }: FilterPanelProps) {
    return (
        <aside className={`w-64 flex-shrink-0 border-r border-gray-100 pr-6 ${className}`}>
            <FilterSection
                title="Category"
                items={CATEGORIES}
                selectedValues={filters.category}
                onToggle={(val) => onToggle('category', val)}
            />

            <FilterSection
                title="Risk Level"
                items={RISKS}
                selectedValues={filters.risk}
                onToggle={(val) => onToggle('risk', val)}
            />

            <FilterSection
                title="Fees"
                items={FEE_BANDS}
                selectedValues={filters.fee_band}
                onToggle={(val) => onToggle('fee_band', val)}
            />

            <FilterSection
                title="AMC"
                items={TOP_AMCS}
                selectedValues={filters.amc}
                onToggle={(val) => onToggle('amc', val)}
            />
        </aside>
    );
}
