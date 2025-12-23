import { useState, useEffect } from 'react';
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

// Helper to extract short name from full AMC name
function getAmcShortName(fullName: string): string {
    // Extract common abbreviations from full names
    if (fullName.includes('SCB ')) return 'SCBAM';
    if (fullName.includes('KASIKORN')) return 'KAsset';
    if (fullName.includes('BBL ')) return 'BBLAM';
    if (fullName.includes('KRUNGSRI')) return 'Krungsri';
    if (fullName.includes('KIATNAKIN')) return 'Kiatnakin';
    if (fullName.includes('KRUNG THAI')) return 'KTAM';
    if (fullName.includes('MFC ')) return 'MFC';
    if (fullName.includes('TISCO')) return 'TISCO';
    if (fullName.includes('UOB ')) return 'UOBAM';
    if (fullName.includes('EASTSPRING')) return 'Eastspring';
    
    // Fallback: first word or first 10 chars
    const firstWord = fullName.split(' ')[0];
    return firstWord.length > 15 ? fullName.substring(0, 15) : firstWord;
}

export function FilterPanel({ filters, onToggle, className = '' }: FilterPanelProps) {
    const [amcOptions, setAmcOptions] = useState<Array<{ label: string; value: string }>>([]);

    useEffect(() => {
        // Fetch AMC list from API
        const fetchAmcs = async () => {
            try {
                const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
                const response = await fetch(`${API_BASE_URL}/funds/amcs`);
                if (response.ok) {
                    const amcs = await response.json();
                    // Take top 10 AMCs by fund count and format for display
                    const formatted = amcs.slice(0, 10).map((amc: any) => ({
                        label: `${getAmcShortName(amc.name_en)} (${amc.fund_count})`,
                        value: amc.id
                    }));
                    setAmcOptions(formatted);
                }
            } catch (error) {
                console.error('Failed to fetch AMCs:', error);
                // Fallback: use empty array, filters will still work if users know IDs
                setAmcOptions([]);
            }
        };

        fetchAmcs();
    }, []);

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
                items={amcOptions}
                selectedValues={filters.amc}
                onToggle={(val) => onToggle('amc', val)}
            />
        </aside>
    );
}
