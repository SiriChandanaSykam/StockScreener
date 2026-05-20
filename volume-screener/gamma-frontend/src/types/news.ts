/**
 * News Intelligence Engine - TypeScript Types
 */

export interface NewsItem {
    id: string;
    ticker: string;
    company_name: string | null;
    headline: string;
    source_url: string | null;
    source_name: string;
    published_at: string;
    created_at: string;
    category: string | null;

    // AI Analysis (flattened)
    relevance_score: number | null;
    sentiment: 'Bullish' | 'Bearish' | 'Neutral' | null;
    sentiment_score: number | null;
    priority: 'critical' | 'high' | 'medium' | 'low' | 'noise' | null;
    ai_summary: string | null;

    // Status
    is_processed: boolean;
    is_alerted: boolean;

    // Full AI analysis
    ai_analysis: {
        relevance_score?: number;
        sentiment?: string;
        summary?: string;
        category?: string;
        confidence?: number;
        key_metrics?: Record<string, unknown>;
        reasoning?: string;
        affected_tickers?: string[];
    } | null;
}

export interface NewsFeedResponse {
    items: NewsItem[];
    total: number;
    limit: number;
    offset: number;
    has_more: boolean;
}

export interface NewsLatestResponse {
    items: NewsItem[];
    count: number;
    latest_id: string | null;
    latest_timestamp: string | null;
}

export interface NewsStats {
    total_items: number;
    processed_items: number;
    unprocessed_items: number;
    items_today: number;
    items_by_source: Record<string, number>;
    items_by_sentiment: Record<string, number>;
}

export interface NewsFeedFilters {
    min_relevance?: number;
    ticker?: string;
    sentiment?: string;
    category?: string;
    priority?: string;
    source?: string;
    limit?: number;
    offset?: number;
    processed_only?: boolean;
}
