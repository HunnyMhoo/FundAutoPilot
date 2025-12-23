import { useState, useCallback, useRef, useEffect } from 'react';
import { FundSummary, CatalogState } from '@/types/fund';
import { fetchFunds, FundFilters, SortOption } from '@/utils/api/funds';

export function useFundCatalog(initialAsOfDate?: string) {
    // State
    const [funds, setFunds] = useState<FundSummary[]>([]);
    const [state, setState] = useState<CatalogState>('idle');
    const [nextCursor, setNextCursor] = useState<string | null>(null);
    const [asOfDate, setAsOfDate] = useState<string>(initialAsOfDate || '');
    const [error, setError] = useState<string | null>(null);

    // Filter & Sort State
    const [searchQuery, setSearchQuery] = useState('');
    const [filters, setFilters] = useState<FundFilters>({
        amc: [],
        category: [],
        risk: [],
        fee_band: []
    });
    const [sort, setSort] = useState<SortOption>('name_asc');

    // De-duplication
    const seenIds = useRef(new Set<string>());
    const isLoadingRef = useRef(false);

    // Initial Load / Refetch from scratch (Page 1)
    const loadInitial = useCallback(async (
        q: string = searchQuery,
        currentFilters: FundFilters = filters,
        currentSort: SortOption = sort
    ) => {
        if (isLoadingRef.current) return;

        isLoadingRef.current = true;
        setState('loading_initial');
        setError(null);
        seenIds.current.clear(); // Reset dupe check on fresh load

        try {
            // No cursor = Page 1
            const response = await fetchFunds(undefined, 25, q, currentFilters, currentSort);

            const uniqueFunds = response.items.filter(fund => {
                if (seenIds.current.has(fund.fund_id)) return false;
                seenIds.current.add(fund.fund_id);
                return true;
            });

            setFunds(uniqueFunds);
            setNextCursor(response.next_cursor);
            setAsOfDate(response.as_of_date);
            setState(uniqueFunds.length === 0 ? 'idle' :
                response.next_cursor ? 'loaded' : 'end_of_results');
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load funds');
            setState('error_initial');
        } finally {
            isLoadingRef.current = false;
        }
    }, [searchQuery, filters, sort]);

    // Load More (Next Page) - USES EXISTING STATE
    const loadMore = useCallback(async () => {
        if (isLoadingRef.current || !nextCursor) return;

        isLoadingRef.current = true;
        setState('loading_more');
        setError(null);

        try {
            const response = await fetchFunds(nextCursor, 25, searchQuery, filters, sort);

            const uniqueFunds = response.items.filter(fund => {
                if (seenIds.current.has(fund.fund_id)) return false;
                seenIds.current.add(fund.fund_id);
                return true;
            });

            setFunds(prev => [...prev, ...uniqueFunds]);
            setNextCursor(response.next_cursor);
            setState(response.next_cursor ? 'loaded' : 'end_of_results');
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load more funds');
            setState('error_load_more');
        } finally {
            isLoadingRef.current = false;
        }
    }, [nextCursor, searchQuery, filters, sort]);

    // --- Actions ---

    // 1. Search Debounce is handled by UI component usually, but here we just accept a new query
    const updateSearch = (q: string) => {
        setSearchQuery(q);
    };

    // 2. Filter Updates
    const toggleFilter = (type: keyof FundFilters, value: string) => {
        setFilters(prev => {
            const current = prev[type];
            const next = current.includes(value)
                ? current.filter(v => v !== value)
                : [...current, value];
            return { ...prev, [type]: next };
        });
    };

    const clearFilters = () => {
        setFilters({ amc: [], category: [], risk: [], fee_band: [] });
    };

    const removeFilter = (type: keyof FundFilters, value: string) => {
        setFilters(prev => ({
            ...prev,
            [type]: prev[type].filter(v => v !== value)
        }));
    };

    // 3. Sort Update
    const updateSort = (s: SortOption) => {
        setSort(s);
    };

    // --- Effects ---

    // Trigger reload when Constraints Change (Query, Filters, Sort)
    // We use a ref to track if it's the very first mount or just a change
    const isFirstRun = useRef(true);

    useEffect(() => {
        // Skip first run? Or rely on UI to trigger? 
        // Usually good to load empty state or default.
        if (isFirstRun.current) {
            isFirstRun.current = false;
            loadInitial();
            return;
        }

        // On any constraint change, strictly reload from Page 1
        // We pass the current state explicitly to be safe, though callback closes over it
        loadInitial(searchQuery, filters, sort);
    }, [searchQuery, filters, sort]); // Intentionally exclude loadInitial to avoid loop

    return {
        funds,
        state,
        error,
        asOfDate,
        loadMore,
        // Constraints
        searchQuery,
        filters,
        sort,
        // Actions
        updateSearch,
        toggleFilter,
        clearFilters,
        removeFilter,
        updateSort,
        // Manual Reload
        reload: () => loadInitial(searchQuery, filters, sort)
    };
}
