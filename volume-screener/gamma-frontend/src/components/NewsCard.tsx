/**
 * NewsCard - Smart component for displaying AI-analyzed news
 * 
 * Features:
 * - Relevance score badge (color-coded)
 * - Sentiment indicator (arrow icons)
 * - AI summary prominently displayed
 * - Affected tickers as clickable chips
 * - Expandable raw details
 */

import React, { useState } from 'react';
import type { NewsItem } from '../types/news';

interface NewsCardProps {
    item: NewsItem;
    onTickerClick?: (ticker: string) => void;
    onCardClick?: (item: NewsItem) => void;
    isNew?: boolean;
}

/**
 * Get color classes for relevance score badge
 */
function getScoreBadgeClasses(score: number | null): string {
    if (!score) return 'bg-gray-600 text-gray-200';
    if (score >= 8) return 'bg-emerald-500 text-white'; // High impact - Green
    if (score >= 4) return 'bg-amber-500 text-white';   // Medium - Yellow/Amber
    return 'bg-gray-600 text-gray-300';                 // Low - Gray
}

/**
 * Get priority badge styling
 */
function getPriorityClasses(priority: string | null): string {
    switch (priority) {
        case 'critical':
            return 'bg-red-500/20 text-red-400 border-red-500/30';
        case 'high':
            return 'bg-orange-500/20 text-orange-400 border-orange-500/30';
        case 'medium':
            return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
        case 'low':
            return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
        default:
            return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
    }
}

/**
 * Sentiment indicator component
 */
function SentimentIndicator({ sentiment, score }: { sentiment: string | null; score: number | null }) {
    if (sentiment === 'Bullish') {
        return (
            <div className="flex items-center gap-1 text-emerald-400">
                <span className="text-lg">⬆️</span>
                <span className="text-xs font-medium">Bullish</span>
            </div>
        );
    }
    if (sentiment === 'Bearish') {
        return (
            <div className="flex items-center gap-1 text-red-400">
                <span className="text-lg">⬇️</span>
                <span className="text-xs font-medium">Bearish</span>
            </div>
        );
    }
    return (
        <div className="flex items-center gap-1 text-gray-400">
            <span className="text-lg">➡️</span>
            <span className="text-xs font-medium">Neutral</span>
        </div>
    );
}

/**
 * Ticker chip component
 */
function TickerChip({ ticker, onClick }: { ticker: string; onClick?: () => void }) {
    return (
        <button
            onClick={(e) => {
                e.stopPropagation();
                onClick?.();
            }}
            className="px-2 py-0.5 text-xs font-mono font-bold rounded 
                 bg-indigo-500/20 text-indigo-300 border border-indigo-500/30
                 hover:bg-indigo-500/30 hover:text-indigo-200 
                 transition-all cursor-pointer"
        >
            {ticker}
        </button>
    );
}

/**
 * Format relative time
 */
function formatRelativeTime(dateString: string): string {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString('en-IN', {
        day: 'numeric',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit'
    });
}

export function NewsCard({ item, onTickerClick, onCardClick, isNew = false }: NewsCardProps) {
    const [showRaw, setShowRaw] = useState(false);

    // Extract affected tickers from AI analysis
    const affectedTickers = item.ai_analysis?.affected_tickers || [item.ticker];

    // Get the summary - prefer AI summary, fallback to headline
    const summary = item.ai_summary || item.ai_analysis?.summary;

    return (
        <div
            className={`
        relative bg-gray-800/50 rounded-lg border transition-all duration-300
        hover:bg-gray-800/70 hover:border-gray-600
        ${isNew ? 'border-indigo-500/50 animate-pulse-once' : 'border-gray-700/50'}
        ${onCardClick ? 'cursor-pointer' : ''}
      `}
            onClick={() => onCardClick?.(item)}
        >
            {/* New Item Indicator */}
            {isNew && (
                <div className="absolute -top-1 -right-1 w-3 h-3 bg-indigo-500 rounded-full animate-ping" />
            )}

            <div className="p-4">
                {/* Header Row: Score, Sentiment, Time */}
                <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                        {/* Relevance Score Badge */}
                        <div
                            className={`
                px-2.5 py-1 rounded-full text-sm font-bold
                ${getScoreBadgeClasses(item.relevance_score)}
              `}
                            title={`Relevance Score: ${item.relevance_score || 'N/A'}/10`}
                        >
                            {item.relevance_score ?? '?'}/10
                        </div>

                        {/* Sentiment Indicator */}
                        <SentimentIndicator
                            sentiment={item.ai_analysis?.sentiment || item.sentiment}
                            score={item.sentiment_score}
                        />

                        {/* Priority Badge */}
                        {item.priority && item.priority !== 'noise' && (
                            <span
                                className={`
                  px-2 py-0.5 text-xs font-medium rounded border
                  ${getPriorityClasses(item.priority)}
                `}
                            >
                                {item.priority.toUpperCase()}
                            </span>
                        )}
                    </div>

                    {/* Time & Source */}
                    <div className="flex items-center gap-2 text-xs text-gray-500">
                        <span>{item.source_name}</span>
                        <span>•</span>
                        <span>{formatRelativeTime(item.published_at)}</span>
                    </div>
                </div>

                {/* AI Summary - Prominent */}
                {summary && (
                    <div className="mb-3 p-3 bg-gray-900/50 rounded-lg border border-gray-700/30">
                        <p className="text-base font-semibold text-gray-100 leading-snug">
                            💡 {summary}
                        </p>
                    </div>
                )}

                {/* Headline */}
                <h3 className="text-sm text-gray-300 mb-3 line-clamp-2">
                    {item.headline}
                </h3>

                {/* Tickers Row */}
                <div className="flex items-center gap-2 mb-3 flex-wrap">
                    <span className="text-xs text-gray-500">Tickers:</span>
                    {affectedTickers.map((ticker) => (
                        <TickerChip
                            key={ticker}
                            ticker={ticker}
                            onClick={() => onTickerClick?.(ticker)}
                        />
                    ))}

                    {/* Category chip */}
                    {item.category && (
                        <span className="px-2 py-0.5 text-xs rounded bg-gray-700/50 text-gray-400">
                            {item.category.replace('_', ' ')}
                        </span>
                    )}
                </div>

                {/* Footer: Actions */}
                <div className="flex items-center justify-between pt-2 border-t border-gray-700/30">
                    <div className="flex items-center gap-2">
                        {/* PDF Link */}
                        {item.source_url && (
                            <a
                                href={item.source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                onClick={(e) => e.stopPropagation()}
                                className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
                            >
                                📄 View Filing
                            </a>
                        )}
                    </div>

                    {/* Show Raw Button */}
                    <button
                        onClick={(e) => {
                            e.stopPropagation();
                            setShowRaw(!showRaw);
                        }}
                        className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
                    >
                        {showRaw ? '▲ Hide Details' : '▼ Show Details'}
                    </button>
                </div>

                {/* Expandable Raw Details */}
                {showRaw && (
                    <div className="mt-3 p-3 bg-gray-900/70 rounded-lg text-xs font-mono overflow-x-auto">
                        <div className="space-y-2 text-gray-400">
                            <div><span className="text-gray-500">ID:</span> {item.id}</div>
                            <div><span className="text-gray-500">Company:</span> {item.company_name}</div>
                            <div><span className="text-gray-500">Published:</span> {new Date(item.published_at).toLocaleString()}</div>
                            <div><span className="text-gray-500">Processed:</span> {item.is_processed ? 'Yes' : 'No'}</div>

                            {item.ai_analysis && (
                                <div className="mt-2 pt-2 border-t border-gray-700">
                                    <div className="text-gray-500 mb-1">AI Analysis:</div>
                                    <pre className="whitespace-pre-wrap text-gray-400">
                                        {JSON.stringify(item.ai_analysis, null, 2)}
                                    </pre>
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

/**
 * Skeleton loader for NewsCard
 */
export function NewsCardSkeleton() {
    return (
        <div className="bg-gray-800/50 rounded-lg border border-gray-700/50 p-4 animate-pulse">
            <div className="flex items-center gap-3 mb-3">
                <div className="w-16 h-6 bg-gray-700 rounded-full" />
                <div className="w-20 h-5 bg-gray-700 rounded" />
            </div>
            <div className="h-12 bg-gray-700 rounded mb-3" />
            <div className="h-4 bg-gray-700 rounded w-3/4 mb-3" />
            <div className="flex gap-2">
                <div className="w-12 h-5 bg-gray-700 rounded" />
                <div className="w-12 h-5 bg-gray-700 rounded" />
            </div>
        </div>
    );
}

export default NewsCard;
