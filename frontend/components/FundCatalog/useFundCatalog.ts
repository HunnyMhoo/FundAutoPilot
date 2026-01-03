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
    const hasLoadedFundsRef = useRef(false);

    // Initial Load / Refetch from scratch (Page 1)
    const loadInitial = useCallback(async (
        q: string = searchQuery,
        currentFilters: FundFilters = filters,
        currentSort: SortOption = sort,
        isInitialLoad: boolean = false
    ) => {
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/7f418701-bce6-449b-9ec6-0178fb2b8930',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'useFundCatalog.ts:33',message:'loadInitial called',data:{isLoading:isLoadingRef.current,q,currentFilters,currentSort,isInitialLoad},timestamp:Date.now(),sessionId:'debug-session',runId:'post-fix',hypothesisId:'B'})}).catch(()=>{});
        // #endregion
        if (isLoadingRef.current) {
            // #region agent log
            fetch('http://127.0.0.1:7242/ingest/7f418701-bce6-449b-9ec6-0178fb2b8930',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'useFundCatalog.ts:35',message:'loadInitial blocked - already loading',data:{},timestamp:Date.now(),sessionId:'debug-session',runId:'post-fix',hypothesisId:'D'})}).catch(()=>{});
            // #endregion
            return;
        }

        isLoadingRef.current = true;
        // Only set loading_initial on the very first load, not on search/filter updates
        // This prevents glitching by keeping current results visible during search
        const shouldShowLoading = isInitialLoad || !hasLoadedFundsRef.current;
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/7f418701-bce6-449b-9ec6-0178fb2b8930',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'useFundCatalog.ts:loadInitial-start',message:'loadInitial starting',data:{q,isInitialLoad,hasLoadedFunds:hasLoadedFundsRef.current,shouldShowLoading,currentState:state},timestamp:Date.now(),sessionId:'debug-session',runId:'post-fix2',hypothesisId:'B,E'})}).catch(()=>{});
        // #endregion
        if (shouldShowLoading) {
            // #region agent log
            fetch('http://127.0.0.1:7242/ingest/7f418701-bce6-449b-9ec6-0178fb2b8930',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'useFundCatalog.ts:setState-loading',message:'Setting state to loading_initial (initial load)',data:{q,isInitialLoad,hasLoadedFunds:hasLoadedFundsRef.current},timestamp:Date.now(),sessionId:'debug-session',runId:'post-fix2',hypothesisId:'B,E'})}).catch(()=>{});
            // #endregion
            setState('loading_initial');
        } else {
            // #region agent log
            fetch('http://127.0.0.1:7242/ingest/7f418701-bce6-449b-9ec6-0178fb2b8930',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'useFundCatalog.ts:setState-skip',message:'Skipping loading_initial (search update) - keeping current state',data:{q,hasLoadedFunds:hasLoadedFundsRef.current,currentState:state},timestamp:Date.now(),sessionId:'debug-session',runId:'post-fix2',hypothesisId:'B,E'})}).catch(()=>{});
            // #endregion
            // Keep current state visible during search updates to prevent glitching
            // Don't change state here - let it stay as 'loaded' or whatever it was
        }
        setError(null);
        seenIds.current.clear(); // Reset dupe check on fresh load
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/7f418701-bce6-449b-9ec6-0178fb2b8930',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'useFundCatalog.ts:38',message:'Before fetchFunds call',data:{q,currentFilters,currentSort},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
        // #endregion

        try {
            // No cursor = Page 1
            const response = await fetchFunds(undefined, 25, q, currentFilters, currentSort);
            // #region agent log
            fetch('http://127.0.0.1:7242/ingest/7f418701-bce6-449b-9ec6-0178fb2b8930',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'useFundCatalog.ts:43',message:'fetchFunds response received',data:{itemsCount:response?.items?.length||0,hasItems:!!response?.items,hasNextCursor:!!response?.next_cursor,responseKeys:response?Object.keys(response):[],asOfDate:response?.as_of_date},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C,E'})}).catch(()=>{});
            // #endregion

            const uniqueFunds = response.items.filter(fund => {
                if (seenIds.current.has(fund.fund_id)) return false;
                seenIds.current.add(fund.fund_id);
                return true;
            });
            // #region agent log
            fetch('http://127.0.0.1:7242/ingest/7f418701-bce6-449b-9ec6-0178fb2b8930',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'useFundCatalog.ts:50',message:'After filtering unique funds',data:{uniqueCount:uniqueFunds.length,originalCount:response.items.length},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{});
            // #endregion

            setFunds(uniqueFunds);
            setNextCursor(response.next_cursor);
            setAsOfDate(response.as_of_date);
            hasLoadedFundsRef.current = true; // Mark that we've successfully loaded funds
            const newState = uniqueFunds.length === 0 ? 'idle' :
                response.next_cursor ? 'loaded' : 'end_of_results';
            // #region agent log
            fetch('http://127.0.0.1:7242/ingest/7f418701-bce6-449b-9ec6-0178fb2b8930',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'useFundCatalog.ts:54',message:'Setting state after success',data:{newState,uniqueFundsLength:uniqueFunds.length,hasNextCursor:!!response.next_cursor},timestamp:Date.now(),sessionId:'debug-session',runId:'post-fix',hypothesisId:'C'})}).catch(()=>{});
            // #endregion
            setState(newState);
        } catch (err) {
            // #region agent log
            fetch('http://127.0.0.1:7242/ingest/7f418701-bce6-449b-9ec6-0178fb2b8930',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'useFundCatalog.ts:57',message:'Error in loadInitial',data:{errorMessage:err instanceof Error?err.message:String(err),errorType:err?.constructor?.name},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
            // #endregion
            setError(err instanceof Error ? err.message : 'Failed to load funds');
            setState('error_initial');
        } finally {
            isLoadingRef.current = false;
            // #region agent log
            fetch('http://127.0.0.1:7242/ingest/7f418701-bce6-449b-9ec6-0178fb2b8930',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'useFundCatalog.ts:60',message:'loadInitial finally block',data:{isLoadingAfter:isLoadingRef.current},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'D'})}).catch(()=>{});
            // #endregion
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
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/7f418701-bce6-449b-9ec6-0178fb2b8930',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'useFundCatalog.ts:updateSearch',message:'updateSearch called',data:{newQuery:q,oldQuery:searchQuery,currentState:state},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B,C'})}).catch(()=>{});
        // #endregion
        setSearchQuery(q);
    };
    
    // Clear search while preserving filters and sort
    const clearSearch = () => {
        setSearchQuery('');
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
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/7f418701-bce6-449b-9ec6-0178fb2b8930',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'useFundCatalog.ts:useEffect',message:'useEffect triggered',data:{isFirstRun:isFirstRun.current,searchQuery,filters,sort,currentState:state,isLoading:isLoadingRef.current},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B,D'})}).catch(()=>{});
        // #endregion
        // Skip first run? Or rely on UI to trigger? 
        // Usually good to load empty state or default.
        if (isFirstRun.current) {
            // #region agent log
            fetch('http://127.0.0.1:7242/ingest/7f418701-bce6-449b-9ec6-0178fb2b8930',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'useFundCatalog.ts:firstRun',message:'First run - calling loadInitial',data:{},timestamp:Date.now(),sessionId:'debug-session',runId:'post-fix',hypothesisId:'B'})}).catch(()=>{});
            // #endregion
            isFirstRun.current = false;
            loadInitial(undefined, undefined, undefined, true);
            return;
        }

        // On any constraint change, strictly reload from Page 1
        // We pass the current state explicitly to be safe, though callback closes over it
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/7f418701-bce6-449b-9ec6-0178fb2b8930',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'useFundCatalog.ts:constraintChange',message:'Constraint change - calling loadInitial',data:{searchQuery,filters,sort,currentState:state},timestamp:Date.now(),sessionId:'debug-session',runId:'post-fix',hypothesisId:'B,E'})}).catch(()=>{});
        // #endregion
        loadInitial(searchQuery, filters, sort, false);
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
        clearSearch,
        toggleFilter,
        clearFilters,
        removeFilter,
        updateSort,
        // Manual Reload
        reload: () => loadInitial(searchQuery, filters, sort, false)
    };
}
