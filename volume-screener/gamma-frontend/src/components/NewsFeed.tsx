/**
 * NewsFeed - Main page for News Intelligence Engine
 * 
 * Features:
 * - Live news feed with polling
 * - Filter controls (relevance, ticker, sentiment)
 * - New items indicator
 * - Infinite scroll / Load more
 */

import React, { useState, useCallback } from 'react';
import { useNewsStream } from '../hooks/useNewsStream';
import { NewsCard, NewsCardSkeleton } from './NewsCard';
import type { NewsItem, NewsFeedFilters } from '../types/news';

interface NewsFeedProps {
    /** Optional: Navigate to stock detail when ticker is clicked */
    onTickerClick?: (ticker: string) => void;
    /** Optional: Handle news item click */
    onItemClick?: (item: NewsItem) => void;
}

export function NewsFeed({ onTickerClick, onItemClick }: NewsFeedProps) {
    // Filter state
    const [filters, setFilters] = useState<NewsFeedFilters>({
        min_relevance: 0,
        limit: 30,
    });
    const [tickerFilter, setTickerFilter] = useState('');
    const [sentimentFilter, setSentimentFilter] = useState('');

    // News stream hook
    const {
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
    } = useNewsStream({
        filters,
        pollInterval: 30000, // 30 seconds
        enablePolling: true,
        pollMinRelevance: filters.min_relevance,
    });

    // Handle filter changes
    const handleRelevanceChange = useCallback((value: number) => {
        setFilters(prev => ({ ...prev, min_relevance: value }));
    }, []);

    const handleTickerSubmit = useCallback((e: React.FormEvent) => {
        e.preventDefault();
        setFilters(prev => ({
            ...prev,
            ticker: tickerFilter.toUpperCase() || undefined
        }));
    }, [tickerFilter]);

    const handleSentimentChange = useCallback((value: string) => {
        setSentimentFilter(value);
        setFilters(prev => ({
            ...prev,
            sentiment: value || undefined
        }));
    }, []);

    const clearFilters = useCallback(() => {
        setTickerFilter('');
        setSentimentFilter('');
        setFilters({ min_relevance: 0, limit: 30 });
    }, []);

    // Mark items as "new" if they arrived via polling

    const handleScrollToNew = useCallback(() => {
        clearNewItems();
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }, [clearNewItems]);

    return (
        <div className="min-h-screen bg-gray-900 text-white">
            {/* Header */}
            <div className="sticky top-0 z-10 bg-gray-900/95 backdrop-blur-sm border-b border-gray-800">
                <div className="max-w-4xl mx-auto px-4 py-4">
                    <div className="flex items-center justify-between mb-4">
                        <div>
                            <a href="/" className="text-gray-400 text-sm hover:text-white mb-2 inline-block">← Back to Dashboard</a>
                            <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                                📰 News Intelligence
                                {isPolling && (
                                    <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"
                                        title="Live polling active" />
                                )}
                            </h1>
                            <p className="text-sm text-gray-400">
                                {total} total items • Polling every 30s
                            </p>
                        </div>

                        <button
                            onClick={refresh}
                            disabled={isLoading}
                            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-lg 
                       text-sm font-medium transition-colors disabled:opacity-50"
                        >
                            {isLoading ? '⏳ Loading...' : '🔄 Refresh'}
                        </button>
                    </div>

                    {/* Filters */}
                    <div className="flex flex-wrap items-center gap-3">
                        {/* Relevance Slider */}
                        <div className="flex items-center gap-2">
                            <label className="text-xs text-gray-400">Min Score:</label>
                            <input
                                type="range"
                                min="0"
                                max="10"
                                value={filters.min_relevance || 0}
                                onChange={(e) => handleRelevanceChange(Number(e.target.value))}
                                className="w-24 h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
                            />
                            <span className="text-sm font-mono text-indigo-400 w-6">
                                {filters.min_relevance || 0}
                            </span>
                        </div>

                        {/* Ticker Filter */}
                        <form onSubmit={handleTickerSubmit} className="flex items-center gap-1">
                            <input
                                type="text"
                                placeholder="Ticker..."
                                value={tickerFilter}
                                onChange={(e) => setTickerFilter(e.target.value)}
                                className="w-24 px-2 py-1 text-sm bg-gray-800 border border-gray-700 
                         rounded focus:border-indigo-500 focus:outline-none"
                            />
                            <button
                                type="submit"
                                className="px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 rounded"
                            >
                                Go
                            </button>
                        </form>

                        {/* Sentiment Filter */}
                        <select
                            value={sentimentFilter}
                            onChange={(e) => handleSentimentChange(e.target.value)}
                            className="px-2 py-1 text-sm bg-gray-800 border border-gray-700 
                       rounded focus:border-indigo-500 focus:outline-none"
                        >
                            <option value="">All Sentiment</option>
                            <option value="Bullish">🟢 Bullish</option>
                            <option value="Bearish">🔴 Bearish</option>
                            <option value="Neutral">⚪ Neutral</option>
                        </select>

                        {/* Clear Filters */}
                        {((filters.min_relevance || 0) > 0 || filters.ticker || filters.sentiment) && (
                            <button
                                onClick={clearFilters}
                                className="text-xs text-gray-400 hover:text-white underline"
                            >
                                Clear filters
                            </button>
                        )}
                    </div>
                </div>
            </div>

            {/* New Items Banner */}
            {newItemsCount > 0 && (
                <div className="sticky top-[120px] z-10 max-w-4xl mx-auto px-4 py-2">
                    <button
                        onClick={handleScrollToNew}
                        className="w-full py-2 bg-indigo-600 hover:bg-indigo-700 rounded-lg
                     text-sm font-medium transition-colors animate-bounce-subtle"
                    >
                        ⬆️ {newItemsCount} new {newItemsCount === 1 ? 'item' : 'items'} - Click to view
                    </button>
                </div>
            )}

            {/* Content */}
            <div className="max-w-4xl mx-auto px-4 py-6">
                {/* Error State */}
                {error && (
                    <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg mb-4">
                        <p className="text-red-400">
                            ⚠️ Error loading news: {error.message}
                        </p>
                        <button
                            onClick={refresh}
                            className="mt-2 text-sm text-red-300 hover:text-white underline"
                        >
                            Try again
                        </button>
                    </div>
                )}

                {/* Loading State */}
                {isLoading && data.length === 0 && (
                    <div className="space-y-4">
                        {[...Array(5)].map((_, i) => (
                            <NewsCardSkeleton key={i} />
                        ))}
                    </div>
                )}

                {/* Empty State */}
                {!isLoading && data.length === 0 && (
                    <div className="text-center py-12">
                        <p className="text-gray-400 text-lg mb-2">No news items found</p>
                        <p className="text-gray-500 text-sm">
                            {(filters.min_relevance || 0) > 0 || filters.ticker
                                ? 'Try adjusting your filters'
                                : 'News will appear here once ingested'}
                        </p>
                    </div>
                )}

                {/* News Cards */}
                <div className="space-y-4">
                    {data.map((item, index) => (
                        <NewsCard
                            key={item.id}
                            item={item}
                            onTickerClick={onTickerClick}
                            onCardClick={onItemClick}
                            isNew={index < newItemsCount}
                        />
                    ))}
                </div>

                {/* Load More */}
                {hasMore && !isLoading && (
                    <div className="mt-6 text-center">
                        <button
                            onClick={loadMore}
                            className="px-6 py-2 bg-gray-800 hover:bg-gray-700 
                       rounded-lg text-sm transition-colors"
                        >
                            Load More ({data.length} of {total})
                        </button>
                    </div>
                )}

                {/* Footer */}
                <div className="mt-8 pt-4 border-t border-gray-800 text-center text-xs text-gray-500">
                    News Intelligence Engine • Powered by AI Analysis
                </div>
            </div>

            {/* CSS for animations */}
            <style>{`
        @keyframes bounce-subtle {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-2px); }
        }
        .animate-bounce-subtle {
          animation: bounce-subtle 2s ease-in-out infinite;
        }
        @keyframes pulse-once {
          0% { opacity: 0.5; transform: scale(0.98); }
          50% { opacity: 1; transform: scale(1); }
          100% { opacity: 1; transform: scale(1); }
        }
        .animate-pulse-once {
          animation: pulse-once 0.5s ease-out forwards;
        }
      `}</style>
        </div>
    );
}

export default NewsFeed;
