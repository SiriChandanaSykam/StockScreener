/**
 * useNewsStream - React Hook for News Intelligence Engine
 * 
 * Features:
 * - Loads initial data from GET /news/feed
 * - Polls GET /news/latest every 30 seconds
 * - Prepends new items without page refresh
 * - Handles loading, error, and empty states
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import type { NewsItem, NewsFeedResponse, NewsLatestResponse, NewsFeedFilters } from '../types/news';

// API Base URL - adjust if needed
const API_BASE_URL = 'http://localhost:8001';

interface UseNewsStreamOptions {
    /** Initial filters for the feed */
    filters?: NewsFeedFilters;
    /** Polling interval in milliseconds (default: 30000) */
    pollInterval?: number;
    /** Enable/disable polling (default: true) */
    enablePolling?: boolean;
    /** Minimum relevance for polling (default: 0) */
    pollMinRelevance?: number;
}

interface UseNewsStreamReturn {
    /** News items array */
    data: NewsItem[];
    /** Loading state for initial fetch */
    isLoading: boolean;
    /** Error state */
    error: Error | null;
    /** Is currently polling */
    isPolling: boolean;
    /** New items count since last view */
    newItemsCount: number;
    /** Refresh the feed manually */
    refresh: () => Promise<void>;
    /** Load more items (pagination) */
    loadMore: () => Promise<void>;
    /** Has more items to load */
    hasMore: boolean;
    /** Total items matching filters */
    total: number;
    /** Clear new items indicator */
    clearNewItems: () => void;
}

export function useNewsStream(options: UseNewsStreamOptions = {}): UseNewsStreamReturn {
    const {
        filters = {},
        pollInterval = 30000, // 30 seconds
        enablePolling = true,
        pollMinRelevance = 0,
    } = options;

    // State
    const [data, setData] = useState<NewsItem[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<Error | null>(null);
    const [isPolling, setIsPolling] = useState(false);
    const [newItemsCount, setNewItemsCount] = useState(0);
    const [hasMore, setHasMore] = useState(false);
    const [total, setTotal] = useState(0);
    const [offset, setOffset] = useState(0);

    // Refs for polling
    const latestIdRef = useRef<string | null>(null);
    const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

    /**
     * Build query string from filters
     */
    const buildQueryString = useCallback((params: Record<string, unknown>): string => {
        const searchParams = new URLSearchParams();
        Object.entries(params).forEach(([key, value]) => {
            if (value !== undefined && value !== null && value !== '') {
                searchParams.append(key, String(value));
            }
        });
        return searchParams.toString();
    }, []);

    /**
     * Fetch initial/paginated news feed
     */
    const fetchFeed = useCallback(async (reset = false): Promise<void> => {
        try {
            if (reset) {
                setIsLoading(true);
                setOffset(0);
            }

            const currentOffset = reset ? 0 : offset;
            const queryParams = buildQueryString({
                ...filters,
                offset: currentOffset,
                limit: filters.limit || 50,
            });

            const response = await fetch(`${API_BASE_URL}/news/feed?${queryParams}`);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const result: NewsFeedResponse = await response.json();

            setData(prev => {
                if (reset) {
                    return result.items;
                }
                // Append for pagination, avoiding duplicates
                const existingIds = new Set(prev.map(item => item.id));
                const newItems = result.items.filter(item => !existingIds.has(item.id));
                return [...prev, ...newItems];
            });

            setTotal(result.total);
            setHasMore(result.has_more);
            setOffset(currentOffset + result.items.length);
            setError(null);

            // Set latest ID for polling reference
            if (result.items.length > 0) {
                latestIdRef.current = result.items[0].id;
            }
        } catch (err) {
            setError(err instanceof Error ? err : new Error('Failed to fetch news'));
            console.error('News feed fetch error:', err);
        } finally {
            setIsLoading(false);
        }
    }, [filters, offset, buildQueryString]);

    /**
     * Poll for latest news
     */
    const pollLatest = useCallback(async (): Promise<void> => {
        if (!latestIdRef.current) return;

        try {
            setIsPolling(true);

            const queryParams = buildQueryString({
                since_id: latestIdRef.current,
                min_relevance: pollMinRelevance,
                limit: 20,
            });

            const response = await fetch(`${API_BASE_URL}/news/latest?${queryParams}`);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const result: NewsLatestResponse = await response.json();

            if (result.items.length > 0) {
                // Prepend new items to the beginning
                setData(prev => {
                    const existingIds = new Set(prev.map(item => item.id));
                    const newItems = result.items.filter(item => !existingIds.has(item.id));

                    if (newItems.length > 0) {
                        setNewItemsCount(count => count + newItems.length);
                        console.log(`📰 ${newItems.length} new news items received`);
                    }

                    return [...newItems, ...prev];
                });

                // Update latest ID reference
                if (result.latest_id) {
                    latestIdRef.current = result.latest_id;
                }
            }
        } catch (err) {
            console.error('Polling error:', err);
            // Don't set error state for polling failures - just log
        } finally {
            setIsPolling(false);
        }
    }, [buildQueryString, pollMinRelevance]);

    /**
     * Refresh the entire feed
     */
    const refresh = useCallback(async (): Promise<void> => {
        setNewItemsCount(0);
        await fetchFeed(true);
    }, [fetchFeed]);

    /**
     * Load more items (pagination)
     */
    const loadMore = useCallback(async (): Promise<void> => {
        if (!hasMore || isLoading) return;
        await fetchFeed(false);
    }, [fetchFeed, hasMore, isLoading]);

    /**
     * Clear new items indicator
     */
    const clearNewItems = useCallback(() => {
        setNewItemsCount(0);
    }, []);

    // Initial fetch
    useEffect(() => {
        fetchFeed(true);
    }, []);  // Only run on mount

    // Re-fetch when filters change
    useEffect(() => {
        const filtersKey = JSON.stringify(filters);
        fetchFeed(true);
    }, [JSON.stringify(filters)]);

    // Setup polling interval
    useEffect(() => {
        if (!enablePolling) return;

        // Start polling after initial load
        pollIntervalRef.current = setInterval(() => {
            pollLatest();
        }, pollInterval);

        return () => {
            if (pollIntervalRef.current) {
                clearInterval(pollIntervalRef.current);
            }
        };
    }, [enablePolling, pollInterval, pollLatest]);

    return {
        data,
        isLoading,
        error,
        isPolling,
        newItemsCount,
        refresh,
        loadMore,
        hasMore,
        total,
        clearNewItems,
    };
}

/**
 * Convenience hook to fetch a single news item
 */
export function useNewsItem(newsId: string | null) {
    const [data, setData] = useState<NewsItem | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<Error | null>(null);

    useEffect(() => {
        if (!newsId) {
            setData(null);
            return;
        }

        const fetchItem = async () => {
            try {
                setIsLoading(true);
                const response = await fetch(`${API_BASE_URL}/news/${newsId}`);

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                const result = await response.json();
                setData(result);
                setError(null);
            } catch (err) {
                setError(err instanceof Error ? err : new Error('Failed to fetch'));
            } finally {
                setIsLoading(false);
            }
        };

        fetchItem();
    }, [newsId]);

    return { data, isLoading, error };
}

/**
 * Hook to search news headlines
 */
export function useNewsSearch(query: string, limit: number = 30) {
    const [data, setData] = useState<NewsItem[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<Error | null>(null);

    useEffect(() => {
        if (!query || query.length < 2) {
            setData([]);
            return;
        }

        const searchNews = async () => {
            try {
                setIsLoading(true);
                const response = await fetch(
                    `${API_BASE_URL}/news/search?q=${encodeURIComponent(query)}&limit=${limit}`
                );

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                const result = await response.json();
                setData(result.items);
                setError(null);
            } catch (err) {
                setError(err instanceof Error ? err : new Error('Search failed'));
            } finally {
                setIsLoading(false);
            }
        };

        // Debounce search
        const timeoutId = setTimeout(searchNews, 300);
        return () => clearTimeout(timeoutId);
    }, [query, limit]);

    return { data, isLoading, error, count: data.length };
}

/**
 * Hook to get news digest summary
 */
export function useNewsDigest(hours: number = 24, minScore: number = 5) {
    const [data, setData] = useState<{
        summary: { total: number; high_impact: number; bullish: number; bearish: number };
        top_items: NewsItem[];
        top_tickers: { ticker: string; count: number }[];
    } | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<Error | null>(null);

    useEffect(() => {
        const fetchDigest = async () => {
            try {
                setIsLoading(true);
                const response = await fetch(
                    `${API_BASE_URL}/news/digest?hours=${hours}&min_score=${minScore}`
                );

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                const result = await response.json();
                setData(result);
                setError(null);
            } catch (err) {
                setError(err instanceof Error ? err : new Error('Failed to fetch digest'));
            } finally {
                setIsLoading(false);
            }
        };

        fetchDigest();
    }, [hours, minScore]);

    return { data, isLoading, error };
}

export default useNewsStream;
