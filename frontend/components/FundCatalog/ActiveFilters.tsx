import { FundFilters } from '@/utils/api/funds';

interface ActiveFiltersProps {
    filters: FundFilters;
    onRemove: (type: keyof FundFilters, value: string) => void;
    onClearAll: () => void;
}

export function ActiveFilters({ filters, onRemove, onClearAll }: ActiveFiltersProps) {
    const hasFilters = Object.values(filters).some(arr => arr.length > 0);

    if (!hasFilters) return null;

    return (
        <div className="flex flex-wrap items-center gap-2 mb-4">
            {Object.entries(filters).map(([type, values]) =>
                values.map(val => (
                    <span
                        key={`${type}-${val}`}
                        className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-brand-primary/10 text-brand-primary border border-brand-primary/20"
                    >
                        {/* Make labels human readable here ideally */}
                        {val}
                        <button
                            type="button"
                            onClick={() => onRemove(type as keyof FundFilters, val)}
                            className="flex-shrink-0 ml-1.5 h-4 w-4 rounded-full inline-flex items-center justify-center text-brand-primary/60 hover:bg-brand-primary/20 hover:text-brand-primary focus:outline-none"
                        >
                            <span className="sr-only">Remove filter</span>
                            <svg className="h-2 w-2" stroke="currentColor" fill="none" viewBox="0 0 8 8">
                                <path strokeLinecap="round" strokeWidth="1.5" d="M1 1l6 6m0-6L1 7" />
                            </svg>
                        </button>
                    </span>
                ))
            )}

            <button
                onClick={onClearAll}
                className="text-xs text-gray-500 hover:text-brand-primary underline ml-2"
            >
                Clear all
            </button>
        </div>
    );
}
