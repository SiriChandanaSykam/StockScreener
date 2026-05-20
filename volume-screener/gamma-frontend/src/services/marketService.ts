/**
 * Market Service - Calls Python FastAPI backend
 * With real stock analysis and TradingView charts
 */

import type { StockData, NewsItem } from '../types';

const API_BASE = 'http://localhost:8000';

const fetchAPI = async <T>(endpoint: string): Promise<T> => {
    const response = await fetch(`${API_BASE}${endpoint}`);
    if (!response.ok) {
        throw new Error(`API error: ${response.statusText}`);
    }
    return response.json();
};

// ============================================================
// ANALYZED STOCKS (Real historical data from yfinance)
// ============================================================

export interface AnalyzedStock {
    symbol: string;
    name: string;
    sector: string;
    price: number;
    change1d: number;
    change5d: number;
    change20d: number;
    change3m: number;
    rsi: number;
    macdSignal: string;
    aboveSma20: boolean;
    aboveSma50: boolean;
    aboveSma200: boolean;
    rvol: number;
    volumeSurge: boolean;
    pctFrom52wHigh: number;
    pctFrom52wLow: number;
    nearBreakout: boolean;
    momentumScore: number;
    volumeScore: number;
    technicalScore: number;
    trendScore: number;
    compositeScore: number;
    rank: number;
    signals: string[];
    analysis: string;
}

export const fetchAnalyzedStocks = async (
    n: number = 50,
    useNifty50: boolean = true,
    universeLimit: number = 500
): Promise<AnalyzedStock[]> => {
    try {
        const data = await fetchAPI<{
            stocks: AnalyzedStock[];
            analyzedCount: number;
            universeLimit: number;
            timestamp: string;
            source: string;
        }>(`/analyze?n=${n}&use_nifty50=${useNifty50}&universe_limit=${universeLimit}`);
        return data.stocks;
    } catch (error) {
        console.error('Failed to fetch analyzed stocks:', error);
        return [];
    }
};

export const fetchStockAnalysis = async (symbol: string): Promise<AnalyzedStock | null> => {
    try {
        return await fetchAPI<AnalyzedStock>(`/analyze/${symbol}`);
    } catch (error) {
        console.error(`Failed to analyze ${symbol}:`, error);
        return null;
    }
};

// Search for stocks in the universe
export interface SearchResult {
    symbol: string;
    name: string;
    sector: string;
}

export const searchSymbols = async (query: string, limit: number = 20): Promise<SearchResult[]> => {
    try {
        const data = await fetchAPI<{ results: SearchResult[]; total: number }>(`/symbols/search?q=${encodeURIComponent(query)}&limit=${limit}`);
        return data.results || [];
    } catch (error) {
        console.error('Failed to search symbols:', error);
        return [];
    }
};

// Get all symbols with pagination
export const getAllSymbols = async (limit: number = 100, offset: number = 0): Promise<SearchResult[]> => {
    try {
        const data = await fetchAPI<{ symbols: SearchResult[]; total: number }>(`/symbols?limit=${limit}&offset=${offset}`);
        return data.symbols || [];
    } catch (error) {
        console.error('Failed to get symbols:', error);
        return [];
    }
};

// ============================================================
// TRADINGVIEW CHARTS
// ============================================================

export const getChartUrl = (symbol: string, period: string = '3mo'): string => {
    return `${API_BASE}/chart-html/${symbol}?period=${period}`;
};

export const fetchChartData = async (symbol: string, period: string = '3mo') => {
    try {
        return await fetchAPI<{
            symbol: string;
            period: string;
            dataSource: string;
            chart: string;
            lastPrice: number;
            change1d: number;
            high52w: number;
            low52w: number;
            timestamp: string;
        }>(`/chart/${symbol}?period=${period}`);
    } catch (error) {
        console.error(`Failed to fetch chart for ${symbol}:`, error);
        return null;
    }
};

// ============================================================
// LEGACY ENDPOINTS (Keep for backward compatibility)
// ============================================================

export const fetchMarketData = async (limit: number = 200): Promise<StockData[]> => {
    try {
        const data = await fetchAPI<{ stocks: StockData[]; lastUpdated: string; pagination?: any }>(`/market-data?limit=${limit}`);
        return data.stocks;
    } catch (error) {
        console.error('Failed to fetch market data:', error);
        return [];
    }
};

export const simulateLiveMarket = (currentStocks: StockData[]): StockData[] => {
    return currentStocks.map(stock => {
        if (Math.random() > 0.4) return stock;

        const volatility = stock.price * 0.0003;
        const change = (Math.random() * volatility * 2) - volatility;
        let newPrice = stock.price + change;
        if (newPrice < 0.05) newPrice = 0.05;

        const percentChangeDelta = (change / stock.price) * 100;
        const newChangePercent = stock.changePercent + percentChangeDelta;

        return {
            ...stock,
            price: newPrice,
            changePercent: newChangePercent
        };
    });
};

export const fetchNewsAnalysis = async (): Promise<NewsItem[]> => {
    try {
        return await fetchAPI<NewsItem[]>('/news');
    } catch (error) {
        console.error('Failed to fetch news:', error);
        return [];
    }
};

export const fetchTopPredictions = async (n: number = 3) => {
    try {
        return await fetchAPI<{
            symbol: string;
            price: number;
            predictedClose: number;
            upside: number;
            confidence: number;
        }[]>(`/predictions/top?n=${n}`);
    } catch (error) {
        console.error('Failed to fetch predictions:', error);
        return [];
    }
};

// ============================================================
// CANDLESTICK PATTERNS
// ============================================================

export interface Pattern {
    name: string;
    bias: 'bullish' | 'bearish' | 'neutral';
    signal: 'BUY' | 'SELL' | 'NEUTRAL';
}

export const fetchPatterns = async (symbol: string, period: string = '3mo'): Promise<Pattern[]> => {
    try {
        const data = await fetchAPI<{
            symbol: string;
            patterns: Pattern[];
            patternCount: number;
            lastPrice: number;
            timestamp: string;
        }>(`/patterns/${symbol}?period=${period}`);
        return data.patterns || [];
    } catch (error) {
        console.error(`Failed to fetch patterns for ${symbol}:`, error);
        return [];
    }
};

// ============================================================
// TRADING SIGNALS (Multi-Strategy)
// ============================================================

export interface TradingSignal {
    strategy: string;
    signal: 'BUY' | 'SELL' | 'NEUTRAL';
    reason: string;
    confidence: number;
}

export interface SignalsResponse {
    symbol: string;
    currentPrice: number;
    signals: TradingSignal[];
    signalCount: number;
    overallSignal: 'BUY' | 'SELL' | 'NEUTRAL';
    buyVotes: number;
    sellVotes: number;
    timestamp: string;
}

export const fetchSignals = async (symbol: string, period: string = '3mo'): Promise<SignalsResponse | null> => {
    try {
        return await fetchAPI<SignalsResponse>(`/signals/${symbol}?period=${period}`);
    } catch (error) {
        console.error(`Failed to fetch signals for ${symbol}:`, error);
        return null;
    }
};

// ============================================================
// SECTOR ANALYSIS
// ============================================================

export interface Sector {
    name: string;
    count: number;
    stocks: { symbol: string; name: string }[];
}

export const fetchSectors = async (): Promise<Sector[]> => {
    try {
        const data = await fetchAPI<{ sectors: Sector[]; totalSectors: number; totalStocks: number }>('/sectors');
        return data.sectors || [];
    } catch (error) {
        console.error('Failed to fetch sectors:', error);
        return [];
    }
};

export const analyzeSector = async (sectorName: string, limit: number = 20): Promise<AnalyzedStock[]> => {
    try {
        const data = await fetchAPI<{
            sector: string;
            stocks: AnalyzedStock[];
            analyzedCount: number;
            totalInSector: number;
            timestamp: string;
        }>(`/sectors/${encodeURIComponent(sectorName)}/analyze?limit=${limit}`);
        return data.stocks || [];
    } catch (error) {
        console.error(`Failed to analyze sector ${sectorName}:`, error);
        return [];
    }
};
