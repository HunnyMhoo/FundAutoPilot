import { useState, useEffect, useCallback } from 'react';
import { FilterSection } from './FilterSection';
import { FundFilters, fetchCategories, fetchRisks, fetchAMCs, CategoryItem, RiskItem, AMCItem } from '@/utils/api/funds';

interface FilterPanelProps {
    filters: FundFilters;
    onToggle: (type: keyof FundFilters, value: string) => void;
    className?: string;
}

const FEE_BANDS = [
    { label: 'Low (≤ 1.0%)', value: 'low' },
    { label: 'Medium (1-2%)', value: 'medium' },
    { label: 'High (> 2.0%)', value: 'high' },
];

// Helper to format category label with count
function formatCategoryLabel(item: CategoryItem): string {
    return `${item.value} (${item.count})`;
}

// Helper to format risk label with count
function formatRiskLabel(item: RiskItem): string {
    return `Level ${item.value} (${item.count})`;
}

// Helper to format AMC label with count
function formatAMCLabel(item: AMCItem): string {
    return `${item.name} (${item.count})`;
}

export function FilterPanel({ filters, onToggle, className = '' }: FilterPanelProps) {
    // State for filter options
    const [categories, setCategories] = useState<CategoryItem[]>([]);
    const [risks, setRisks] = useState<RiskItem[]>([]);
    const [amcOptions, setAmcOptions] = useState<AMCItem[]>([]);
    
    // State for loading and errors
    const [categoriesLoading, setCategoriesLoading] = useState(true);
    const [categoriesError, setCategoriesError] = useState<string | null>(null);
    const [risksLoading, setRisksLoading] = useState(true);
    const [risksError, setRisksError] = useState<string | null>(null);
    
    // AMC search state
    const [amcSearchTerm, setAmcSearchTerm] = useState('');
    const [amcLoading, setAmcLoading] = useState(false);
    const [amcError, setAmcError] = useState<string | null>(null);
    const [amcCursor, setAmcCursor] = useState<string | null>(null);
    const [hasMoreAMCs, setHasMoreAMCs] = useState(false);
    
    // Debounce timer for AMC search
    const [debounceTimer, setDebounceTimer] = useState<NodeJS.Timeout | null>(null);
    
    // Load categories on mount
    useEffect(() => {
        const loadCategories = async () => {
            setCategoriesLoading(true);
            setCategoriesError(null);
            try {
                const response = await fetchCategories();
                setCategories(response.items);
            } catch (error) {
                console.error('Failed to fetch categories:', error);
                setCategoriesError(error instanceof Error ? error.message : 'Failed to load categories');
            } finally {
                setCategoriesLoading(false);
            }
        };
        
        loadCategories();
    }, []);
    
    // Load risks on mount
    useEffect(() => {
        const loadRisks = async () => {
            setRisksLoading(true);
            setRisksError(null);
            try {
                const response = await fetchRisks();
                setRisks(response.items);
            } catch (error) {
                console.error('Failed to fetch risks:', error);
                setRisksError(error instanceof Error ? error.message : 'Failed to load risks');
            } finally {
                setRisksLoading(false);
            }
        };
        
        loadRisks();
    }, []);
    
    // Load initial AMCs on mount (empty search = all AMCs)
    useEffect(() => {
        const loadInitialAMCs = async () => {
            setAmcLoading(true);
            setAmcError(null);
            try {
                const response = await fetchAMCs('', 20, null);
                setAmcOptions(response.items);
                setAmcCursor(response.next_cursor);
                setHasMoreAMCs(response.next_cursor !== null);
            } catch (error) {
                console.error('Failed to fetch AMCs:', error);
                setAmcError(error instanceof Error ? error.message : 'Failed to load AMCs');
            } finally {
                setAmcLoading(false);
            }
        };
        
        loadInitialAMCs();
    }, []);
    
    // Debounced AMC search
    useEffect(() => {
        // Clear existing timer
        if (debounceTimer) {
            clearTimeout(debounceTimer);
        }
        
        // Set new timer
        const timer = setTimeout(() => {
            const searchAMCs = async () => {
                setAmcLoading(true);
                setAmcError(null);
                try {
                    const response = await fetchAMCs(amcSearchTerm || undefined, 20, null);
                    setAmcOptions(response.items);
                    setAmcCursor(response.next_cursor);
                    setHasMoreAMCs(response.next_cursor !== null);
                } catch (error) {
                    console.error('Failed to search AMCs:', error);
                    setAmcError(error instanceof Error ? error.message : 'Failed to search AMCs');
                } finally {
                    setAmcLoading(false);
                }
            };
            
            searchAMCs();
        }, 300); // 300ms debounce
        
        setDebounceTimer(timer);
        
        // Cleanup
        return () => {
            if (timer) {
                clearTimeout(timer);
            }
        };
    }, [amcSearchTerm]);
    
    // Load more AMCs (pagination)
    const loadMoreAMCs = useCallback(async () => {
        if (!amcCursor || amcLoading) return;
        
        setAmcLoading(true);
        try {
            const response = await fetchAMCs(amcSearchTerm || undefined, 20, amcCursor);
            setAmcOptions(prev => [...prev, ...response.items]);
            setAmcCursor(response.next_cursor);
            setHasMoreAMCs(response.next_cursor !== null);
        } catch (error) {
            console.error('Failed to load more AMCs:', error);
            setAmcError(error instanceof Error ? error.message : 'Failed to load more AMCs');
        } finally {
            setAmcLoading(false);
        }
    }, [amcCursor, amcSearchTerm, amcLoading]);
    
    // Format filter items for FilterSection
    const categoryItems = categories.map(cat => ({
        label: formatCategoryLabel(cat),
        value: cat.value,
        count: cat.count
    }));
    
    const riskItems = risks.map(risk => ({
        label: formatRiskLabel(risk),
        value: risk.value,
        count: risk.count
    }));
    
    const amcItems = amcOptions.map(amc => ({
        label: formatAMCLabel(amc),
        value: amc.id,
        count: amc.count
    }));
    
    return (
        <aside className={`w-64 flex-shrink-0 border-r border-gray-100 pr-6 ${className}`}>
            {/* Categories Section */}
            <div className="mb-6">
                <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider mb-3">
                    Category
                </h3>
                {categoriesLoading ? (
                    <div className="text-sm text-gray-500">Loading categories...</div>
                ) : categoriesError ? (
                    <div className="text-sm text-red-600">
                        {categoriesError}
                        <button
                            onClick={() => window.location.reload()}
                            className="ml-2 text-blue-600 underline"
                        >
                            Retry
                        </button>
                    </div>
                ) : (
                    <FilterSection
                        title=""
                        items={categoryItems}
                        selectedValues={filters.category}
                        onToggle={(val) => onToggle('category', val)}
                    />
                )}
            </div>
            
            {/* Risk Level Section */}
            <div className="mb-6">
                <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider mb-3">
                    Risk Level
                </h3>
                {risksLoading ? (
                    <div className="text-sm text-gray-500">Loading risks...</div>
                ) : risksError ? (
                    <div className="text-sm text-red-600">
                        {risksError}
                        <button
                            onClick={() => window.location.reload()}
                            className="ml-2 text-blue-600 underline"
                        >
                            Retry
                        </button>
                    </div>
                ) : (
                    <FilterSection
                        title=""
                        items={riskItems}
                        selectedValues={filters.risk}
                        onToggle={(val) => onToggle('risk', val)}
                    />
                )}
            </div>
            
            {/* Fees Section (unchanged - static) */}
            <FilterSection
                title="Fees"
                items={FEE_BANDS}
                selectedValues={filters.fee_band}
                onToggle={(val) => onToggle('fee_band', val)}
            />
            
            {/* AMC Section with Typeahead */}
            <div className="mb-6">
                <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider mb-3">
                    AMC
                </h3>
                <div className="mb-3">
                    <input
                        type="text"
                        placeholder="Search AMC..."
                        value={amcSearchTerm}
                        onChange={(e) => setAmcSearchTerm(e.target.value)}
                        className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary"
                    />
                </div>
                {amcLoading && amcOptions.length === 0 ? (
                    <div className="text-sm text-gray-500">Loading AMCs...</div>
                ) : amcError ? (
                    <div className="text-sm text-red-600">
                        {amcError}
                        <button
                            onClick={() => {
                                setAmcError(null);
                                setAmcSearchTerm('');
                            }}
                            className="ml-2 text-blue-600 underline"
                        >
                            Retry
                        </button>
                    </div>
                ) : amcOptions.length === 0 ? (
                    <div className="text-sm text-gray-500">No AMCs found</div>
                ) : (
                    <>
                        <FilterSection
                            title=""
                            items={amcItems}
                            selectedValues={filters.amc}
                            onToggle={(val) => onToggle('amc', val)}
                        />
                        {hasMoreAMCs && (
                            <button
                                onClick={loadMoreAMCs}
                                disabled={amcLoading}
                                className="mt-2 text-sm text-blue-600 hover:text-blue-800 underline disabled:text-gray-400"
                            >
                                {amcLoading ? 'Loading...' : 'Load more'}
                            </button>
                        )}
                    </>
                )}
            </div>
        </aside>
    );
}
