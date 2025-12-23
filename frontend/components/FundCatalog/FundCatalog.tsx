'use client';

import { useFundCatalog } from './useFundCatalog';
import { FundCard } from './FundCard';
import { SkeletonLoader } from './SkeletonLoader';
import { LoadMoreButton } from './LoadMoreButton';
import { ErrorState } from './ErrorState';
import { EmptyState } from './EmptyState';
import SearchInput from './SearchInput'; // Assuming default export
import { FilterPanel } from './FilterPanel';
import { SortControl } from './SortControl';
import { ActiveFilters } from './ActiveFilters';
import styles from './FundCatalog.module.css';

interface FundCatalogProps {
    initialAsOfDate?: string;
}

export function FundCatalog({ initialAsOfDate }: FundCatalogProps) {
    const {
        funds,
        state,
        error,
        asOfDate,
        loadMore,
        searchQuery,
        filters,
        sort,
        updateSearch,
        clearSearch,
        toggleFilter,
        clearFilters,
        removeFilter,
        updateSort,
        reload
    } = useFundCatalog(initialAsOfDate);

    // Initial Loading State
    if (state === 'loading_initial') {
        return (
            <div className={styles.container}>
                <header className={styles.header}>
                    <h1 className={styles.title}>Fund Catalog</h1>
                    <p className={styles.subtitle}>Explore mutual funds across all AMCs</p>
                </header>
                <div className="flex gap-8 mt-8">
                    {/* Skeleton Sidebar */}
                    <div className="w-64 flex-shrink-0 hidden md:block">
                        <div className="h-8 bg-gray-100 rounded mb-6 w-1/2"></div>
                        <div className="space-y-3">
                            {[1, 2, 3, 4].map(i => <div key={i} className="h-4 bg-gray-100 rounded w-3/4"></div>)}
                        </div>
                    </div>
                    {/* Main Content */}
                    <div className="flex-1">
                        <div className="h-12 bg-gray-100 rounded mb-6"></div>
                        <SkeletonLoader count={6} />
                    </div>
                </div>
            </div>
        );
    }

    if (state === 'error_initial') {
        return (
            <div className={styles.container}>
                <header className={styles.header}>
                    <h1 className={styles.title}>Fund Catalog</h1>
                </header>
                <div className="mt-8">
                    <ErrorState
                        message={error || 'Failed to load funds'}
                        onRetry={reload}
                    />
                </div>
            </div>
        );
    }

    return (
        <div className={styles.container}>
            <header className={styles.header}>
                <div className={styles.headerContent}>
                    <h1 className={styles.title}>Fund Catalog</h1>
                    <p className={styles.subtitle}>
                        Explore mutual funds across all AMCs
                    </p>
                </div>
                {asOfDate && (
                    <div className={styles.dateBadge}>
                        <span className={styles.dateLabel}>Data updated</span>
                        <span className={styles.dateValue}>{asOfDate}</span>
                    </div>
                )}
            </header>

            <div className="flex flex-col md:flex-row gap-8 mt-8">
                {/* Sidebar Filters */}
                <FilterPanel
                    filters={filters}
                    onToggle={toggleFilter}
                    className="hidden md:block"
                />

                {/* Main Content */}
                <main className="flex-1 min-w-0">
                    {/* Controls Row: Search + Sort */}
                    <div className="flex flex-col sm:flex-row gap-4 mb-6">
                        <div className="flex-1">
                            <SearchInput
                                onSearch={updateSearch}
                                initialValue={searchQuery}
                            />
                        </div>
                        <SortControl value={sort} onChange={updateSort} />
                    </div>

                    {/* Active Filters Summary */}
                    <ActiveFilters
                        filters={filters}
                        onRemove={removeFilter}
                        onClearAll={clearFilters}
                    />

                    {/* Results Info */}
                    {searchQuery && (
                        <div className="mb-4 text-sm text-gray-600">
                            <span>Showing results for '{searchQuery}'</span>
                            {funds.length > 0 && (
                                <span className="ml-2 text-gray-500">({funds.length} {funds.length === 1 ? 'fund' : 'funds'})</span>
                            )}
                        </div>
                    )}
                    {!searchQuery && funds.length > 0 && (
                        <div className="mb-4 text-sm text-gray-500">
                            <span>Showing {funds.length} funds</span>
                        </div>
                    )}

                    {/* Empty State */}
                    {state === 'idle' && funds.length === 0 && !error && (
                        <EmptyState
                            onRetry={reload}
                            searchQuery={searchQuery}
                            onClearSearch={clearSearch}
                        />
                    )}

                    {/* Grid */}
                    <div className={styles.grid}>
                        {funds.map((fund) => (
                            <FundCard key={fund.fund_id} fund={fund} />
                        ))}
                    </div>

                    {/* Load More Error */}
                    {state === 'error_load_more' && (
                        <ErrorState
                            message={error || 'Failed to load more funds'}
                            onRetry={loadMore}
                            isInline
                        />
                    )}

                    {/* Load More Button */}
                    <div className={styles.loadMoreContainer}>
                        {funds.length > 0 && (
                            <LoadMoreButton
                                onClick={loadMore}
                                isLoading={state === 'loading_more'}
                                isEndOfResults={state === 'end_of_results'}
                                hasError={state === 'error_load_more'}
                            />
                        )}
                    </div>
                </main>
            </div>
        </div>
    );
}
